@echo off
title Inventario TI - Matrix Edition
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python no esta instalado en este equipo.
    echo Instale Python 3.11+ desde https://www.python.org/downloads/
    pause
    exit /b 1
)

python main.py
if errorlevel 1 pause
