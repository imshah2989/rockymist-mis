@echo off
SETLOCAL EnableDelayedExpansion
TITLE 🏔️ RockyMist-I Financial MIS Launcher

:: --- CONFIGURATION (SYCED WITH YOUR NEW PATHS) ---
SET "APP_DIR=C:\Obizworks\RockyMist Financial MIS"
SET "DB_FILE=G:\My Drive\Obizworks Financial MIS\RockyMist_System.db"
SET "BACKUP_DIR=E:\Obizworks\MIS Finance\Backups"

COLOR 0B
echo ====================================================
echo           ROCKYMIST-I FINANCIAL MIS
echo ====================================================
echo.

:: 1. CHECK GOOGLE DRIVE (G:)
echo [1/4] Checking G: Drive connection...
if not exist "%DB_FILE%" (
    COLOR 0C
    echo ❌ ERROR: Database not found at:
    echo    "%DB_FILE%"
    echo.
    echo CHECKLIST:
    echo 1. Is Google Drive for Desktop running?
    echo 2. Is your folder named exactly "Obizworks Financial MIS"?
    echo 3. Is the file "RockyMist_System.db" inside it?
    pause
    exit
)
echo ✅ Google Drive Connected.

:: 2. CHECK AI ENGINE (OLLAMA)
echo [2/4] Checking AI Engine (Ollama)...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="1" (
    echo ⚠️ AI Engine is not running. Starting Ollama...
    :: Use 'start' to launch the tray app without blocking the script
    start "" ollama app
    timeout /t 8
)
echo ✅ AI Engine Active.

:: 3. VERIFY BACKUP PATH (E:)
echo [3/4] Verifying Backup Drive (E:)...
if not exist "%BACKUP_DIR%" (
    echo ⚠️ Warning: Backup drive E: not detected. 
    echo    System will run, but auto-backups will fail.
) else (
    echo ✅ Backup Path Verified.
)

:: 4. LAUNCH STREAMLIT
echo [4/4] Launching MIS Interface...
echo.
echo 🖥️  Keep this window open while using the MIS.
echo ----------------------------------------------------

:: Crucial Debug: Ensure we actually get into the directory
cd /d "%APP_DIR%"
if "%ERRORLEVEL%" NEQ "0" (
    COLOR 0C
    echo ❌ ERROR: Could not find App Directory: "%APP_DIR%"
    pause
    exit
)

:: Run Streamlit using the python module flag
python -m streamlit run MIS_Fin.py --client.toolbarMode=hidden --browser.gatherUsageStats=false

if %ERRORLEVEL% NEQ 0 (
    COLOR 0C
    echo.
    echo ❌ ERROR: Streamlit failed to start. 
    echo    DEBUG STEPS:
    echo    1. Open CMD and type: pip install streamlit pandas openai pdfplumber
    echo    2. Ensure MIS_Fin.py is inside "%APP_DIR%"
    pause
)

pause