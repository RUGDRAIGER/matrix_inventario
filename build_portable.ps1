# Genera paquete portable completo (programa + inventario.db)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$OutDir = Join-Path $Root "dist"
$ZipName = "matrix_inventario_portable.zip"
$ZipPath = Join-Path $OutDir $ZipName
$Staging = Join-Path $OutDir "staging"

Write-Host "Inicializando base de datos..."
Push-Location $Root
python -c "import database as db; db.init_db(); print('DB OK:', db.DB_PATH)"
Pop-Location

if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Path $Staging -Force | Out-Null

$Files = @(
    "main.py", "database.py", "scanner.py", "gui.py", "ui_components.py", "paths.py",
    "requirements.txt", "Iniciar.bat", "inventario.db", "README.md"
)
foreach ($f in $Files) {
    $src = Join-Path $Root $f
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $Staging $f)
    } else {
        Write-Warning "No encontrado: $f"
    }
}

New-Item -ItemType Directory -Path (Join-Path $Staging "backups") -Force | Out-Null

if (Test-Path $OutDir) {} else { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

Compress-Archive -Path (Join-Path $Staging "*") -DestinationPath $ZipPath -Force
Remove-Item $Staging -Recurse -Force

Write-Host "Paquete creado: $ZipPath"
(Get-Item $ZipPath).Length / 1KB | ForEach-Object { Write-Host ("Tamanio: {0:N1} KB" -f $_) }
