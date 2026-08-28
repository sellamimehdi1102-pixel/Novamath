@echo off
setlocal enabledelayedexpansion
title NovaMath v1.88
cd /d "%~dp0"

set PORT=5050
set URL=http://127.0.0.1:%PORT%/

echo ============================================
echo   Lancement de NovaMath v1.88...
echo ============================================
echo.

if not exist "webapp\server.py" (
    echo [ERREUR] Backend : ECHEC - webapp\server.py introuvable dans ce dossier.
    echo Ce dossier de version semble incomplet.
    echo.
    pause
    exit /b 1
)
echo Backend      : OK ^(webapp\server.py trouve^)

if not exist "webapp\static\dashboard.html" (
    echo [ERREUR] Frontend : ECHEC - webapp\static introuvable ou incomplet.
    pause
    exit /b 1
)
echo Frontend     : OK ^(webapp\static trouve^)

rem ── Détection de Python (venv local en priorité, sinon Python système) ─────
set PYTHON=
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
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
echo Demarrage du serveur NovaMath v1.88...
echo (une nouvelle fenetre va s'ouvrir - laisse-la ouverte)
echo.

start "NovaMath v1.88 - Serveur" cmd /k ""!PYTHON!" webapp\server.py"

rem ── Attente que le serveur réponde avant d'ouvrir le navigateur ────────
set WAITED=0
:waitloop
curl -s -o nul -w "%%{http_code}" %URL% > "%TEMP%\novamath_status.txt" 2>nul
set /p STATUS=<"%TEMP%\novamath_status.txt"
if "!STATUS!"=="200" goto ready
if "!STATUS!"=="302" goto ready
set /a WAITED+=1
if !WAITED! geq 30 (
    echo [ERREUR] Le serveur ne repond pas apres 30 secondes.
    echo Regarde la fenetre "NovaMath v1.88 - Serveur" pour le detail de l'erreur.
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
echo NovaMath v1.88 est lance sur %URL%
echo Pour arreter le serveur : ferme la fenetre "NovaMath v1.88 - Serveur".
echo.
pause
