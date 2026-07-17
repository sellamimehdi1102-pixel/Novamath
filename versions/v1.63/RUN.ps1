# NovaMath v1.63 - Lancement (PowerShell)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$Port = 5050
$Url = "http://127.0.0.1:$Port/"

Write-Host "============================================"
Write-Host "  Lancement de NovaMath v1.63..."
Write-Host "============================================"
Write-Host ""

if (-not (Test-Path "webapp\server.py")) {
    Write-Host "[ERREUR] Backend : ECHEC - webapp\server.py introuvable dans ce dossier." -ForegroundColor Red
    Write-Host "Ce dossier de version semble incomplet."
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}
Write-Host "Backend      : OK"

if (-not (Test-Path "webapp\static\dashboard.html")) {
    Write-Host "[ERREUR] Frontend : ECHEC - webapp\static introuvable ou incomplet." -ForegroundColor Red
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}
Write-Host "Frontend     : OK"

# ── Détection de Python (venv local en priorité, sinon Python système) ─────
$PythonCmd = $null
if (Test-Path ".venv\Scripts\python.exe") {
    $PythonCmd = ".venv\Scripts\python.exe"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
}

if (-not $PythonCmd) {
    Write-Host "[ERREUR] Python n'est pas installe ou n'est pas dans le PATH." -ForegroundColor Red
    Write-Host "Telecharge-le depuis https://www.python.org/downloads/"
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}
Write-Host "Python detecte : $PythonCmd"

# ── Vérification des dépendances ────────────────────────────────────────
& $PythonCmd -c "import flask" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Dependances manquantes : installation en cours..."
    if (Test-Path "requirements.txt") {
        & $PythonCmd -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERREUR] Echec de l'installation des dependances." -ForegroundColor Red
            Read-Host "Appuie sur Entree pour fermer"
            exit 1
        }
    } else {
        Write-Host "[ERREUR] requirements.txt introuvable." -ForegroundColor Red
        Read-Host "Appuie sur Entree pour fermer"
        exit 1
    }
}

# ── Vérification du port ───────────────────────────────────────────────
$portInUse = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "[ERREUR] Le port $Port est deja utilise par un autre programme." -ForegroundColor Red
    Write-Host "Ferme l'application qui occupe ce port, ou modifie `$Port` en haut de ce script."
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}

Write-Host "Base de donnees : OK (sera initialisee automatiquement au demarrage)"
Write-Host ""
Write-Host "Demarrage du serveur NovaMath v1.63..."
$serverProcess = Start-Process -FilePath $PythonCmd -ArgumentList "webapp\server.py" -PassThru -WindowStyle Normal

# ── Attente que le serveur réponde avant d'ouvrir le navigateur ────────
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $ready) {
    Write-Host "[ERREUR] Le serveur ne repond pas apres 30 secondes." -ForegroundColor Red
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}

Write-Host "Serveur demarre."
Write-Host "Ouverture du navigateur..."
Start-Process $Url
Write-Host ""
Write-Host "NovaMath v1.63 est lance sur $Url"
Write-Host "Pour arreter le serveur : ferme la fenetre du processus Python (PID $($serverProcess.Id))."
Read-Host "Appuie sur Entree pour fermer cette fenetre (le serveur continue de tourner)"
