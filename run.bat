@echo off
setlocal enabledelayedexpansion
title Movie Recommender Server

echo ========================================================
echo       Starting Movie Recommender Application
echo ========================================================

:: Check if virtual environment exists; create if missing
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Creating venv...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment. Ensure Python 3.10+ is installed and in PATH.
        pause
        exit /b 1
    )
    echo [INFO] Virtual environment created.
    echo [INFO] Installing required dependencies...
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [WARNING] Some dependencies failed to install. Continuing with available packages...
    )
) else (
    call venv\Scripts\activate.bat
)

:: Open the browser in background after 2 seconds
start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

:: Start the Flask backend server
echo [INFO] Starting Flask server on http://localhost:5000 ...
python app.py

pause
