@echo off
title Inventario TI - Matrix Edition
cd /d "%~dp0"

if exist "Inventario.exe" (
    start "" "Inventario.exe"
    exit /b 0
)

where python >nul 2>&1
if errorlevel 1 (
    echo No se encontro Inventario.exe ni Python en este equipo.
    echo Descargue Inventario.exe desde la pagina de descarga.
    pause
    exit /b 1
)

python main.py
if errorlevel 1 pause
