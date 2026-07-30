# Paquete portable completo: Inventario.exe + inventario.db + Iniciar.bat
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$OutDir = Join-Path $Root "dist"
$ZipName = "matrix_inventario_portable.zip"
$ZipPath = Join-Path $OutDir $ZipName
$Staging = Join-Path $OutDir "staging"
$ExeName = "Inventario.exe"

& (Join-Path $Root "build_exe.ps1")

Push-Location $Root
python -c "import database as db; db.init_db()"
Pop-Location

if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Path $Staging -Force | Out-Null

$ExeSrc = Join-Path $OutDir $ExeName
if (-not (Test-Path $ExeSrc)) { throw "Falta $ExeName. Ejecute build_exe.ps1 primero." }
Copy-Item $ExeSrc (Join-Path $Staging $ExeName)

$Bundle = @("Iniciar.bat", "inventario.db", "README.md")
foreach ($f in $Bundle) {
    $src = Join-Path $Root $f
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $Staging $f)
    } else {
        Write-Warning "No encontrado: $f"
    }
}

New-Item -ItemType Directory -Path (Join-Path $Staging "backups") -Force | Out-Null

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

Compress-Archive -Path (Join-Path $Staging "*") -DestinationPath $ZipPath -Force
Remove-Item $Staging -Recurse -Force

Write-Host "Paquete creado: $ZipPath"
(Get-Item $ZipPath).Length / 1MB | ForEach-Object { Write-Host ("Tamanio ZIP: {0:N1} MB" -f $_) }
