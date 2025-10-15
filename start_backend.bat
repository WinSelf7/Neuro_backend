@echo off
REM Start Backend Server Script for Windows

echo ========================================
echo Starting Backend Server
echo ========================================

REM Clear Python cache
echo.
echo [1/3] Clearing Python cache...
python clear_cache.py

REM Check if .env exists
if not exist .env (
    echo.
    echo [!] Warning: .env file not found
    echo [!] Creating .env from template...
    copy env.example.txt .env
    echo [!] Please edit .env with your database credentials
    pause
)

REM Start the server
echo.
echo [2/3] Starting FastAPI server...
echo.
echo Backend will be available at: http://localhost:7861
echo API Documentation at: http://localhost:7861/docs
echo.
echo [3/3] Launching server...
echo.

python api\main.py

pause

