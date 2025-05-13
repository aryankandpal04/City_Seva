# PowerShell script to set up Firebase database collections for CitySeva

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CitySeva Firebase Database Setup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check for Python installation
try {
    $pythonVersion = python --version
    Write-Host "✅ Found Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Python is not installed or not in PATH. Please install Python and try again." -ForegroundColor Red
    exit 1
}

# Check for Firebase key file
$keyFile = "cityseva-4d82b-firebase-adminsdk-fbsvc-a904038f62.json"
if (-not (Test-Path $keyFile)) {
    Write-Host "❌ Error: Firebase key file '$keyFile' not found." -ForegroundColor Red
    Write-Host "Please place your Firebase admin SDK key file in the project directory with this name." -ForegroundColor Yellow
    Write-Host "Or modify the create_collections.py script to use a different key file." -ForegroundColor Yellow
    exit 1
}

# Check for firebase-admin package
try {
    python -c "import firebase_admin" -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing firebase-admin package..." -ForegroundColor Yellow
        python -m pip install firebase_admin
    } else {
        Write-Host "✅ firebase-admin package is already installed" -ForegroundColor Green
    }
} catch {
    Write-Host "Installing firebase-admin package..." -ForegroundColor Yellow
    python -m pip install firebase_admin
}

# Run the collection creation script
Write-Host "Creating Firebase collections..." -ForegroundColor Cyan
python create_collections.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "🔥 Firebase database setup complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Deploy Firestore security rules: firebase deploy --only firestore:rules" -ForegroundColor White
    Write-Host "2. Verify collections in the Firebase console: https://console.firebase.google.com" -ForegroundColor White
    Write-Host "3. Update your app configuration to use Firebase" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "❌ Error occurred during setup. Please check the error messages above." -ForegroundColor Red
    exit 1
}

# Pause so the user can see the output
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 