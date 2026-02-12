# run.ps1 - PowerShell script to setup and run the API server
# Run with: powershell -ExecutionPolicy Bypass -File run.ps1

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Shakwa Multi-Tenant API Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.9+ from https://www.python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if in correct directory
if (-not (Test-Path "requirements.txt")) {
    Write-Host "ERROR: requirements.txt not found" -ForegroundColor Red
    Write-Host "Please run this script from the app_api directory" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
Write-Host "✓ Virtual environment activated" -ForegroundColor Green

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt | Out-Null
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✓ .env created - please edit with your PostgreSQL credentials" -ForegroundColor Green
    Write-Host ""
    Write-Host "Edit .env file with your database credentials, then run this script again." -ForegroundColor Cyan
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 0
}

# Seed database
Write-Host ""
Write-Host "Seeding database with test data..." -ForegroundColor Yellow
python seed_db.py
Write-Host ""

# Start the server
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Starting FastAPI Server..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Swagger Docs: http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "ReDoc Docs:   http://localhost:8000/api/redoc" -ForegroundColor Green
Write-Host "API Root:     http://localhost:8000/" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python -m app.main
