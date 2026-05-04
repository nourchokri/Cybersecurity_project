# Activate virtual environment for the Cybersecurity SOC Platform
# Usage: .\activate.ps1

Write-Host "Activating virtual environment..." -ForegroundColor Green
& .\.venv\Scripts\Activate.ps1

Write-Host "`nVirtual environment activated!" -ForegroundColor Green
Write-Host "To start the Django server, run:" -ForegroundColor Yellow
Write-Host "  cd cybersec_backend" -ForegroundColor Cyan
Write-Host "  python manage.py runserver 8000" -ForegroundColor Cyan
