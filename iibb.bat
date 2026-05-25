@echo off
chcp 65001 >nul
title IIBB - Estudio CG
cd /d "%~dp0"

if not exist .venv\Scripts\activate.bat (
    echo.
    echo ERROR: El entorno virtual no existe.
    echo Primero corri instalar.bat
    echo.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Iniciando IIBB Convenio Multilateral...
streamlit run iibb/main.py --server.headless false --browser.gatherUsageStats false
