@echo off
SETLOCAL EnableDelayedExpansion
TITLE 🏔️ RockyMist-I FinMIS (Decoupled Launcher)

SET "APP_DIR=C:\Obizworks\RockyMist Financial MIS"
SET "DB_FILE=G:\My Drive\Obizworks Financial MIS\RockyMist_System.db"
SET "BACKUP_DIR=E:\Obizworks\MIS Finance\Backups"

COLOR 0B
echo ====================================================
echo           ROCKYMIST-I FINANCIAL MIS (v2.0)
echo ====================================================
echo.

:: 1. CHECK GOOGLE DRIVE (G:)
echo [1/3] Checking G: Drive database persistence...
if not exist "%DB_FILE%" (
    COLOR 0C
    echo ❌ ERROR: Database not found at "%DB_FILE%"
    pause
    exit
)
echo ✅ Google Drive Connected.

:: (Note: AI Engine check removed since we are now using Cerebras Cloud API)

:: 2. VERIFY BACKUP PATH
echo [2/3] Verifying Backup Drive (E:)...
if not exist "%BACKUP_DIR%" (
    echo ⚠️ Warning: Backup drive E: not detected. 
) else (
    echo ✅ Backup Path Verified.
)

:: 3. LAUNCH SERVICES
echo [3/3] Launching Local Servers...
cd /d "%~dp0"

:: Start FastAPI Backend on Port 8000
echo 🚀 Starting FastAPI Backend (Port 8000)...
start "FastAPI Backend" cmd /k "cd backend && uvicorn main:app --host 0.0.0.0 --port 8000"

:: Start Frontend Static Server on Port 3000
echo 🖥️  Starting Frontend Server (Port 3000)...
start "Frontend UI" cmd /k "cd frontend && python -m http.server 3000"

echo.
echo ====================================================
echo ✅ SYSTEM ONLINE
echo ➡️  Open your browser to: http://localhost:3000
echo ➡️  API Docs available at: http://localhost:8000/docs
echo ====================================================
pause