$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
if (-not (Test-Path "$raiz\venv\Scripts\Activate.ps1")) {
    Write-Host "Creando entorno virtual e instalando dependencias..."
    python -m venv "$raiz\venv"
    & "$raiz\venv\Scripts\python.exe" -m pip install -r "$raiz\requirements.txt"
}
& "$raiz\venv\Scripts\Activate.ps1"
Set-Location "$raiz\Licoreria"
python manage.py migrate
Write-Host "Tienda: http://127.0.0.1:8000/   Panel: http://127.0.0.1:8000/acceso/"
python manage.py runserver
