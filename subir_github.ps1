# subir_github.ps1 - guarda el proyecto en Git y lo sube a GitHub con revision de seguridad
param(
    [string]$Repo = "https://github.com/andremezabarriga314/Licoreria.git",
    [string]$Mensaje = "Tienda Libido y Tentacion: catalogo, pedidos, inventario y roles"
)
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

function Fallo($texto) { Write-Host "ERROR: $texto" -ForegroundColor Red; exit 1 }

# 1. Git instalado
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fallo "Git no esta instalado. Ejecuta: winget install Git.Git  (luego cierra y abre la terminal)"
}

# 2. Archivos necesarios
foreach ($f in ".gitignore", "requirements.txt", "Licoreria\manage.py") {
    if (-not (Test-Path $f)) { Fallo "Falta $f. Ejecuta este script dentro de la carpeta Licoreria_." }
}

# 3. Repositorio local
if (-not (Test-Path ".git")) {
    git init -b main 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { git init | Out-Null }
    Write-Host "Repositorio creado."
}

# 4. Identidad
if (-not (git config user.name)) { $n = Read-Host "Tu nombre para Git"; git config user.name $n }
if (-not (git config user.email)) { $c = Read-Host "Tu correo para Git"; git config user.email $c }

# 5. Preparar archivos y REVISAR que no haya nada privado
git add -A
$lista = @(git diff --cached --name-only)
$prohibidos = @('(^|/)venv/', '(^|/)\.venv/', '(^|/)media/', '(^|/)mi_proyecto_respaldo/', '(^|/)__pycache__/',
                '\.sqlite3$', '(^|/)\.env(\..*)?$', '\.bak2?$', '(^|/)respaldo.*\.json$')
$malos = @($lista | Where-Object { $a = $_; @($prohibidos | Where-Object { $a -match $_ }).Count -gt 0 })
if ($malos.Count -gt 0) {
    git reset | Out-Null
    Write-Host "ARCHIVOS PRIVADOS DETECTADOS (no se subio nada):" -ForegroundColor Red
    $malos | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Fallo "Revisa tu .gitignore y vuelve a ejecutar."
}

Write-Host "`nSe van a subir $($lista.Count) archivos:" -ForegroundColor Cyan
$lista | ForEach-Object { Write-Host "  $_" }
$resp = Read-Host "`nEscribe SI para continuar"
if ($resp -ne "SI") { git reset | Out-Null; Fallo "Cancelado. No se subio nada." }

# 6. Commit
if ($lista.Count -gt 0) {
    git commit -m $Mensaje | Out-Null
    if ($LASTEXITCODE -ne 0) { Fallo "No se pudo crear el commit." }
    Write-Host "Commit creado." -ForegroundColor Green
} else {
    Write-Host "No hay cambios nuevos que guardar."
}

# 7. Conectar con GitHub
git remote get-url origin 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) { git remote set-url origin $Repo } else { git remote add origin $Repo }
git branch -M main

# 8. Subir
Write-Host "`nSubiendo a $Repo ..." -ForegroundColor Cyan
Write-Host "(si se abre el navegador, inicia sesion en GitHub)"
git push -u origin main
if ($LASTEXITCODE -ne 0) { Fallo "El push fallo. Si GitHub dice que el repositorio no esta vacio, avisame antes de forzar nada." }
Write-Host "`nListo: $($Repo -replace '\.git$','')" -ForegroundColor Green
