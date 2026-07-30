# Compila InventarioTI.exe (PyInstaller) - portable, sin Python en el PC destino
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DistDir = Join-Path $Root "dist"
$BuildDir = Join-Path $Root "build"
$ExeName = "Inventario"

Push-Location $Root

Write-Host "Verificando PyInstaller..."
python -m pip install -q pyinstaller 2>$null
python -m pip show pyinstaller | Out-Null

Write-Host "Inicializando base de datos..."
python -c "import database as db; db.init_db(); print('DB OK:', db.DB_PATH)"

if (Test-Path $DistDir) {
    Get-ChildItem $DistDir -Filter "$ExeName.exe" -ErrorAction SilentlyContinue | Remove-Item -Force
}

Write-Host "Compilando $ExeName.exe ..."
python -m PyInstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --name $ExeName `
    --distpath $DistDir `
    --workpath $BuildDir `
    --specpath $BuildDir `
    --hidden-import wmi `
    --hidden-import win32timezone `
    --hidden-import pywintypes `
    --collect-all customtkinter `
    main.py

$ExePath = Join-Path $DistDir "$ExeName.exe"
if (-not (Test-Path $ExePath)) {
    throw "No se genero el ejecutable en $ExePath"
}

$sizeMb = (Get-Item $ExePath).Length / 1MB
Write-Host ("Listo: {0} ({1:N1} MB)" -f $ExePath, $sizeMb)

Pop-Location
