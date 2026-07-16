"""
Crée un instantané AUTONOME du site NovaMath dans versions/v{X.YY}/.

Usage :
    python create_version_snapshot.py "Titre court de la version" [--bump minor|major]

Système de versioning (convention unifiée depuis le 2026-07-13) :
- Numérotation décimale professionnelle "vX.YY" (ex: v1.00, v1.01, ..., v1.10, v1.20), toujours
  deux chiffres après le point, "v" minuscule — un seul schéma pour tout le projet NovaMath.
  Les dossiers versions/NovaMath_V1-13 et NovaMath_v1.00-1.31 (anciens schémas, l'un entier, l'autre
  décimal mais préfixé "NovaMath_") ont été renommés une fois pour toutes vers ce schéma unique
  (v1.00 à v1.17) le 2026-07-13 — voir CHANGELOG.md pour la table de correspondance.
- La version courante est lue/écrite dans le fichier racine VERSION (ex: "v1.17", avec le "v").
- --bump minor (défaut) : correction mineure/bugfix -> +0.01 (v1.03 -> v1.04).
- --bump major          : fonctionnalité majeure -> arrondi à la prochaine dizaine du
  numéro mineur (v1.04 -> v1.10, v1.10 -> v1.20), report sur le numéro majeur au-delà de .99
  (v1.99 -> v2.00, jamais "v2" ni "V2").
- La version ne revient JAMAIS en arrière et aucun dossier de version existant n'est jamais
  modifié ni supprimé après sa création (à l'exception de la migration ponctuelle du 2026-07-13
  ci-dessus). Lumis_V1-6 (produit précédent, nom différent) restent hors de ce schéma, intacts.
- webapp/static/js/version.js (source unique affichée dans l'app) est mis à jour avec la
  nouvelle version AVANT la copie, pour que l'instantané et l'app en cours de développement
  affichent la même version.

Organisation du projet :
- La racine du projet contient les ressources partagées "sources" : scripts de génération
  (01-07), sources brutes (Chapitres/, texts/), et les outils (ce script, CHANGELOG.md/TODO.md
  racine).
- versions/v{X.YY}/ est un instantané AUTONOME et déplaçable : il contient sa propre copie de
  webapp/ (server.py + static/), des banques d'exercices (exercises_bank*.json), des modèles IA
  (models/), du programme (Programme AI.json), des données runtime (data/) et de
  requirements.txt, ainsi qu'un fichier de lancement (RUN.bat / RUN.ps1) et un README.md. Une
  version archivée n'est jamais modifiée après coup.

Ce script :
- lit/incrémente automatiquement VERSION à la racine (jamais de retour en arrière),
- met à jour webapp/static/js/version.js avec la nouvelle version,
- copie webapp/, exercises_bank*.json, models/, Programme AI.json, data/, requirements.txt,
- génère RUN.bat, RUN.ps1 et README.md adaptés à cette version (chemins relatifs uniquement,
  bannière affichant la version lancée et un contrôle Backend/Frontend/Base de données),
- crée un gabarit CHANGELOG.md dans versions/v{X.YY}/, à compléter,
- prépend une section "## v{X.YY}" dans le CHANGELOG.md racine (qui liste toutes les versions
  sous un unique titre "# NovaMath"), à compléter avant de considérer la version finalisée,
- ne modifie JAMAIS un dossier de version existant.
"""
import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSIONS_DIR = ROOT / "versions"
VERSION_FILE = ROOT / "VERSION"
VERSION_JS = ROOT / "webapp" / "static" / "js" / "version.js"
ROOT_CHANGELOG = ROOT / "CHANGELOG.md"
PRODUCT_NAME = "NovaMath"
DEFAULT_PORT = 5050

EXCLUDE_DIRS = {"__pycache__"}
EXCLUDE_SUFFIXES = {".pyc"}

# Ressources partagées à dupliquer dans chaque instantané pour qu'il soit autonome.
SHARED_FILES = [
    "exercises_bank.json",
    "exercises_bank_natural.json",
    "exercises_bank_reformulations.json",
    "Programme AI.json",
    "requirements.txt",
]
SHARED_DIRS = ["models", "data"]


def read_current_version():
    """Retourne la version courante SANS le préfixe "v" (usage interne : calculs,
    version.js, RUN.bat...). Le fichier VERSION sur disque, lui, garde le "v"
    (ex: "v1.17") — c'est le format demandé pour ce fichier."""
    if VERSION_FILE.exists():
        v = VERSION_FILE.read_text(encoding="utf-8").strip()
        if v.startswith("v"):
            v = v[1:]
        if re.match(r"^\d+\.\d{2}$", v):
            return v
    return "1.00"


def bump_version(version_str, kind):
    major_s, minor_s = version_str.split(".")
    major, minor = int(major_s), int(minor_s)
    if kind == "major":
        minor = ((minor // 10) + 1) * 10
    else:
        minor += 1
    if minor >= 100:
        major += 1
        minor -= 100
    return f"{major}.{minor:02d}"


def ignore(directory, names):
    ignored = set()
    for name in names:
        full = Path(directory) / name
        if full.is_dir() and name in EXCLUDE_DIRS:
            ignored.add(name)
        elif full.suffix in EXCLUDE_SUFFIXES:
            ignored.add(name)
    return ignored


def detect_port(server_py_path):
    """Lit le port réellement utilisé par ce server.py (app.run(..., port=N)),
    pour ne jamais coder en dur un port qui pourrait diverger d'une version à l'autre."""
    try:
        text = server_py_path.read_text(encoding="utf-8")
        m = re.search(r"app\.run\([^)]*port\s*=\s*(\d+)", text)
        if m:
            return int(m.group(1))
    except OSError:
        pass
    return DEFAULT_PORT


# Gabarit du CHANGELOG.md propre à chaque dossier versions/v{X.YY}/ (un seul
# titre de niveau 1, ce fichier ne documente qu'une seule version).
VERSION_CHANGELOG_TEMPLATE = """# NovaMath v{version}

**Date** : {date}

**Nom de la mise à jour** : {title}

## Nouveautés
- (à compléter)

## Corrections
- (à compléter)

## Optimisations
- (à compléter)

## Fichiers modifiés
- (à compléter)

## Bugs connus
- (à compléter)

## Temps estimé de développement
- (à compléter)
"""

# Gabarit de la section prépendée dans le CHANGELOG.md RACINE (niveau 2, sous
# l'unique titre "# NovaMath" qui liste l'historique complet des versions).
ROOT_CHANGELOG_ENTRY_TEMPLATE = """## v{version}

**Date** : {date}

**Nom de la mise à jour** : {title}

### Nouveautés
- (à compléter)

### Corrections
- (à compléter)

### Optimisations
- (à compléter)

### Fichiers modifiés
- (à compléter)

### Bugs connus
- (à compléter)

### Temps estimé de développement
- (à compléter)
"""

# ── RUN.bat ─────────────────────────────────────────────────────────────────
# Chemins toujours relatifs à %~dp0 (dossier du script) : la version reste
# fonctionnelle si le dossier est déplacé ou renommé, sur n'importe quel PC.
RUN_BAT_TEMPLATE = """@echo off
setlocal enabledelayedexpansion
title {product} v{version}
cd /d "%~dp0"

set PORT={port}
set URL=http://127.0.0.1:%PORT%/

echo ============================================
echo   Lancement de {product} v{version}...
echo ============================================
echo.

if not exist "webapp\\server.py" (
    echo [ERREUR] Backend : ECHEC - webapp\\server.py introuvable dans ce dossier.
    echo Ce dossier de version semble incomplet.
    echo.
    pause
    exit /b 1
)
echo Backend      : OK ^(webapp\\server.py trouve^)

if not exist "webapp\\static\\dashboard.html" (
    echo [ERREUR] Frontend : ECHEC - webapp\\static introuvable ou incomplet.
    pause
    exit /b 1
)
echo Frontend     : OK ^(webapp\\static trouve^)

rem ── Détection de Python (venv local en priorité, sinon Python système) ─────
set PYTHON=
if exist ".venv\\Scripts\\python.exe" (
    set PYTHON=.venv\\Scripts\\python.exe
) else (
    where python >nul 2>nul
    if !errorlevel! equ 0 (
        set PYTHON=python
    ) else (
        where py >nul 2>nul
        if !errorlevel! equ 0 (
            set PYTHON=py -3
        )
    )
)

if "!PYTHON!"=="" (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH.
    echo Telecharge-le depuis https://www.python.org/downloads/
    echo puis relance ce fichier.
    echo.
    pause
    exit /b 1
)

echo Python detecte : !PYTHON!

rem ── Vérification des dépendances ────────────────────────────────────────
!PYTHON! -c "import flask" >nul 2>nul
if !errorlevel! neq 0 (
    echo Dependances manquantes : installation en cours...
    if exist "requirements.txt" (
        !PYTHON! -m pip install -r requirements.txt
        if !errorlevel! neq 0 (
            echo [ERREUR] Echec de l'installation des dependances.
            pause
            exit /b 1
        )
    ) else (
        echo [ERREUR] requirements.txt introuvable, impossible d'installer les dependances.
        pause
        exit /b 1
    )
)

rem ── Vérification du port ───────────────────────────────────────────────
netstat -ano | findstr ":%PORT% " | findstr "LISTENING" >nul
if !errorlevel! equ 0 (
    echo [ERREUR] Le port %PORT% est deja utilise par un autre programme.
    echo Ferme l'application qui occupe ce port, ou modifie la valeur PORT
    echo en haut de ce fichier RUN.bat, puis relance-le.
    echo.
    pause
    exit /b 1
)

echo Base de donnees : OK ^(sera initialisee automatiquement au demarrage^)
echo.
echo Demarrage du serveur {product} v{version}...
echo (une nouvelle fenetre va s'ouvrir - laisse-la ouverte)
echo.

start "{product} v{version} - Serveur" cmd /k ""!PYTHON!" webapp\\server.py"

rem ── Attente que le serveur réponde avant d'ouvrir le navigateur ────────
set WAITED=0
:waitloop
curl -s -o nul -w "%%{{http_code}}" %URL% > "%TEMP%\\novamath_status.txt" 2>nul
set /p STATUS=<"%TEMP%\\novamath_status.txt"
if "!STATUS!"=="200" goto ready
if "!STATUS!"=="302" goto ready
set /a WAITED+=1
if !WAITED! geq 30 (
    echo [ERREUR] Le serveur ne repond pas apres 30 secondes.
    echo Regarde la fenetre "{product} v{version} - Serveur" pour le detail de l'erreur.
    echo.
    pause
    exit /b 1
)
timeout /t 1 /nobreak >nul
goto waitloop

:ready
echo Serveur demarre.
echo Ouverture du navigateur...
start "" "%URL%"
echo.
echo {product} v{version} est lance sur %URL%
echo Pour arreter le serveur : ferme la fenetre "{product} v{version} - Serveur".
echo.
pause
"""

# ── RUN.ps1 ─────────────────────────────────────────────────────────────────
RUN_PS1_TEMPLATE = """# {product} v{version} - Lancement (PowerShell)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$Port = {port}
$Url = "http://127.0.0.1:$Port/"

Write-Host "============================================"
Write-Host "  Lancement de {product} v{version}..."
Write-Host "============================================"
Write-Host ""

if (-not (Test-Path "webapp\\server.py")) {{
    Write-Host "[ERREUR] Backend : ECHEC - webapp\\server.py introuvable dans ce dossier." -ForegroundColor Red
    Write-Host "Ce dossier de version semble incomplet."
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}}
Write-Host "Backend      : OK"

if (-not (Test-Path "webapp\\static\\dashboard.html")) {{
    Write-Host "[ERREUR] Frontend : ECHEC - webapp\\static introuvable ou incomplet." -ForegroundColor Red
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}}
Write-Host "Frontend     : OK"

# ── Détection de Python (venv local en priorité, sinon Python système) ─────
$PythonCmd = $null
if (Test-Path ".venv\\Scripts\\python.exe") {{
    $PythonCmd = ".venv\\Scripts\\python.exe"
}} elseif (Get-Command python -ErrorAction SilentlyContinue) {{
    $PythonCmd = "python"
}} elseif (Get-Command py -ErrorAction SilentlyContinue) {{
    $PythonCmd = "py"
}}

if (-not $PythonCmd) {{
    Write-Host "[ERREUR] Python n'est pas installe ou n'est pas dans le PATH." -ForegroundColor Red
    Write-Host "Telecharge-le depuis https://www.python.org/downloads/"
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}}
Write-Host "Python detecte : $PythonCmd"

# ── Vérification des dépendances ────────────────────────────────────────
& $PythonCmd -c "import flask" 2>$null
if ($LASTEXITCODE -ne 0) {{
    Write-Host "Dependances manquantes : installation en cours..."
    if (Test-Path "requirements.txt") {{
        & $PythonCmd -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {{
            Write-Host "[ERREUR] Echec de l'installation des dependances." -ForegroundColor Red
            Read-Host "Appuie sur Entree pour fermer"
            exit 1
        }}
    }} else {{
        Write-Host "[ERREUR] requirements.txt introuvable." -ForegroundColor Red
        Read-Host "Appuie sur Entree pour fermer"
        exit 1
    }}
}}

# ── Vérification du port ───────────────────────────────────────────────
$portInUse = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($portInUse) {{
    Write-Host "[ERREUR] Le port $Port est deja utilise par un autre programme." -ForegroundColor Red
    Write-Host "Ferme l'application qui occupe ce port, ou modifie `$Port` en haut de ce script."
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}}

Write-Host "Base de donnees : OK (sera initialisee automatiquement au demarrage)"
Write-Host ""
Write-Host "Demarrage du serveur {product} v{version}..."
$serverProcess = Start-Process -FilePath $PythonCmd -ArgumentList "webapp\\server.py" -PassThru -WindowStyle Normal

# ── Attente que le serveur réponde avant d'ouvrir le navigateur ────────
$ready = $false
for ($i = 0; $i -lt 30; $i++) {{
    try {{
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {{ $ready = $true; break }}
    }} catch {{
        Start-Sleep -Seconds 1
    }}
}}

if (-not $ready) {{
    Write-Host "[ERREUR] Le serveur ne repond pas apres 30 secondes." -ForegroundColor Red
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}}

Write-Host "Serveur demarre."
Write-Host "Ouverture du navigateur..."
Start-Process $Url
Write-Host ""
Write-Host "{product} v{version} est lance sur $Url"
Write-Host "Pour arreter le serveur : ferme la fenetre du processus Python (PID $($serverProcess.Id))."
Read-Host "Appuie sur Entree pour fermer cette fenetre (le serveur continue de tourner)"
"""

README_TEMPLATE = """# {product} v{version}

Version autonome de {product} — ce dossier contient tout ce qu'il faut pour la
lancer, y compris les banques d'exercices et les modèles IA. Il peut être
copié ou déplacé sur un autre PC sans configuration supplémentaire (Python
doit simplement être installé).

## Lancer le site

- **Windows (double-clic)** : `RUN.bat`
- **PowerShell** : clic droit sur `RUN.ps1` → *Exécuter avec PowerShell*
  (ou dans un terminal : `powershell -ExecutionPolicy Bypass -File .\\RUN.ps1`)

Le script :
1. vérifie que le backend et le frontend sont bien présents dans ce dossier ;
2. détecte Python (environnement virtuel `.venv/` s'il existe, sinon Python système) ;
3. installe automatiquement les dépendances manquantes (`requirements.txt`) ;
4. démarre le serveur {product} v{version} (la base de données SQLite est
   initialisée automatiquement à ce moment-là si elle n'existe pas encore) ;
5. attend qu'il soit prêt, puis ouvre automatiquement le navigateur sur
   `http://127.0.0.1:{port}/`.

## Arrêter le serveur

Ferme la fenêtre de console du serveur (titrée « {product} v{version} - Serveur »
sous RUN.bat, ou la fenêtre du processus Python sous RUN.ps1), ou tape Ctrl+C
dans cette fenêtre.

## Résolution des erreurs courantes

- **« Python n'est pas installé »** : installe Python depuis
  https://www.python.org/downloads/ (coche « Add Python to PATH » pendant
  l'installation), puis relance RUN.bat.
- **« Le port {port} est déjà utilisé »** : une autre instance de {product}
  (ou un autre programme) écoute déjà sur ce port. Ferme-la, ou modifie la
  valeur du port en haut de RUN.bat / RUN.ps1.
- **« webapp\\server.py introuvable »** : le dossier de version est incomplet
  (fichiers manquants) — reprends une copie complète du dossier.
- **Le navigateur ne s'ouvre pas** : ouvre-le manuellement à l'adresse
  `http://127.0.0.1:{port}/` une fois la fenêtre du serveur affichée.
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("title", nargs="?", default="")
    parser.add_argument("--bump", choices=["minor", "major"], default="minor")
    args = parser.parse_args()

    current = read_current_version()
    version = bump_version(current, args.bump)
    dest = VERSIONS_DIR / f"v{version}"

    if dest.exists():
        print(f"Le dossier {dest} existe déjà — arrêt (une version ne doit jamais être recréée).")
        sys.exit(1)

    # 1) Version.js (source unique affichée dans l'app) mis à jour AVANT la copie,
    #    pour que l'instantané et le dev en cours affichent la même version.
    VERSION_JS.write_text(
        '// ── Source unique de la version affichée dans l\'application ────────────────\n'
        '// Mise à jour automatiquement par create_version_snapshot.py à chaque nouvel\n'
        '// instantané (versions/v{X.XX}/) — ne jamais éditer ce fichier à la\n'
        '// main dans un dossier de version déjà archivé.\n'
        f'export const NOVAMATH_VERSION = "{version}";\n',
        encoding="utf-8",
    )
    VERSION_FILE.write_text(f"v{version}\n", encoding="utf-8")

    VERSIONS_DIR.mkdir(exist_ok=True)
    dest.mkdir()

    shutil.copytree(ROOT / "webapp", dest / "webapp", ignore=ignore)

    for name in SHARED_FILES:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, dest / name)
        else:
            print(f"[avertissement] {name} introuvable à la racine, non copié.")

    for name in SHARED_DIRS:
        src = ROOT / name
        if src.exists():
            shutil.copytree(src, dest / name, ignore=ignore)
        else:
            print(f"[avertissement] {name}/ introuvable à la racine, non copié.")

    port = detect_port(dest / "webapp" / "server.py")
    fmt = dict(product=PRODUCT_NAME, version=version, port=port)

    (dest / "RUN.bat").write_text(RUN_BAT_TEMPLATE.format(**fmt), encoding="utf-8")
    (dest / "RUN.ps1").write_text(RUN_PS1_TEMPLATE.format(**fmt), encoding="utf-8")
    (dest / "README.md").write_text(README_TEMPLATE.format(**fmt), encoding="utf-8")

    version_changelog = VERSION_CHANGELOG_TEMPLATE.format(
        version=version, date=date.today().isoformat(), title=args.title or "(sans titre)",
    )
    (dest / "CHANGELOG.md").write_text(version_changelog, encoding="utf-8")

    # 2) CHANGELOG.md racine : un seul titre "# NovaMath", chaque version est une
    #    section "## v{X.YY}" prépendée juste après ce titre (la plus récente en
    #    tête) — jamais de section existante réécrite.
    root_entry = ROOT_CHANGELOG_ENTRY_TEMPLATE.format(
        version=version, date=date.today().isoformat(), title=args.title or "(sans titre)",
    )
    if ROOT_CHANGELOG.exists():
        existing = ROOT_CHANGELOG.read_text(encoding="utf-8")
        lines = existing.split("\n")
        insert_at = len(lines)
        for i, line in enumerate(lines):
            if line.startswith("## v"):
                insert_at = i
                break
        new_lines = lines[:insert_at] + [root_entry.rstrip("\n"), ""] + lines[insert_at:]
        ROOT_CHANGELOG.write_text("\n".join(new_lines), encoding="utf-8")
    else:
        ROOT_CHANGELOG.write_text(
            "# NovaMath\n\n"
            "Historique complet des versions, la plus récente en tête. Chaque version est aussi "
            "archivée de façon autonome et détaillée dans `versions/v{X.YY}/CHANGELOG.md` "
            "(jamais modifié après coup).\n\n" + root_entry,
            encoding="utf-8",
        )

    print(f"Version {PRODUCT_NAME} v{version} créée dans {dest}")
    print(f"(autonome : webapp/ + banques + modèles + RUN.bat/RUN.ps1 + README.md)")
    if args.title:
        print(f"Titre : {args.title}")
    print(f"-> Compléter {dest / 'CHANGELOG.md'} et la nouvelle entrée en tête de {ROOT_CHANGELOG} avant de considérer la version finalisée.")


if __name__ == "__main__":
    main()
