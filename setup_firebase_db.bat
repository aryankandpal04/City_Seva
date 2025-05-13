@echo off
echo ========================================
echo CitySeva Firebase Database Setup Script
echo ========================================
echo.

REM Check for Python installation
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo X Error: Python is not installed. Please install Python and try again.
    exit /b 1
)

REM Check for Firebase key file
set KEY_FILE=cityseva-4d82b-firebase-adminsdk-fbsvc-a904038f62.json
if not exist %KEY_FILE% (
    echo X Error: Firebase key file '%KEY_FILE%' not found.
    echo Please place your Firebase admin SDK key file in the project directory with this name.
    echo Or modify the create_collections.py script to use a different key file.
    exit /b 1
)

REM Check for firebase-admin package
python -c "import firebase_admin" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing firebase-admin package...
    python -m pip install firebase_admin
)

REM Run the collection creation script
echo Creating Firebase collections...
python create_collections.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo 🔥 Firebase database setup complete!
    echo.
    echo Next steps:
    echo 1. Deploy Firestore security rules: firebase deploy --only firestore:rules
    echo 2. Verify collections in the Firebase console: https://console.firebase.google.com
    echo 3. Update your app configuration to use Firebase
    echo.
) else (
    echo X Error occurred during setup. Please check the error messages above.
    exit /b 1
)

REM Pause so the user can see the output
pause 