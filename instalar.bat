@echo off
chcp 65001 >nul
title Instalador IIBB - Estudio CG
cd /d "%~dp0"

echo.
echo ============================================================
echo   IIBB Convenio Multilateral - Estudio CG
echo   Instalacion inicial
echo ============================================================
echo.

:: Verificar Python
echo [1/5] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python no esta instalado o no esta en el PATH.
    echo Descargalo de https://www.python.org/downloads/
    echo Durante la instalacion marca "Add Python to PATH".
    echo.
    pause
    exit /b 1
)
python --version
echo OK.
echo.

:: Crear entorno virtual
echo [2/5] Creando entorno virtual...
if not exist .venv (
    python -m venv .venv
    echo Entorno virtual creado.
) else (
    echo El entorno virtual ya existe, saltando.
)
echo.

:: Activar entorno e instalar dependencias
echo [3/5] Instalando dependencias (puede tardar 2-5 minutos)...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -e ".[dev]" --quiet
if errorlevel 1 (
    echo.
    echo ERROR: Fallo la instalacion de dependencias.
    echo Copia el mensaje de arriba y compartelo con el soporte.
    pause
    exit /b 1
)
echo OK.
echo.

:: Migraciones Alembic
echo [4/5] Creando base de datos...
alembic upgrade head
if errorlevel 1 (
    echo.
    echo ERROR: Fallo la creacion de la base de datos.
    pause
    exit /b 1
)
echo OK.
echo.

:: Seed
echo [5/5] Cargando datos demo (24 jurisdicciones + American Implant S.A.)...
python -c "from iibb.seed.runner import main; main()"
if errorlevel 1 (
    echo.
    echo AVISO: El seed fallo o ya estaba cargado. La app puede funcionar igual.
)
echo.

echo ============================================================
echo   Instalacion completada exitosamente!
echo.
echo   Para abrir la app: doble clic en iibb.bat
echo ============================================================
echo.
pause
