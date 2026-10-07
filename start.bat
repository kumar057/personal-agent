@echo off
title Aegis - Personal AI Agent
echo ========================================================
echo             AEGIS - PERSONAL LOCAL AI AGENT
echo ========================================================
echo.

cd /d "%~dp0"

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found! Please ensure setup is complete.
    pause
    exit /b
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Starting Aegis Agent...
python run.py

pause
