#!/bin/bash

# Script to set up Firebase database collections for CitySeva

echo "========================================"
echo "CitySeva Firebase Database Setup Script"
echo "========================================"
echo ""

# Check for Python installation
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "❌ Error: Python is not installed. Please install Python and try again."
    exit 1
fi

# Check for Firebase key file
KEY_FILE="cityseva-4d82b-firebase-adminsdk-fbsvc-a904038f62.json"
if [ ! -f "$KEY_FILE" ]; then
    echo "❌ Error: Firebase key file '$KEY_FILE' not found."
    echo "Please place your Firebase admin SDK key file in the project directory with this name."
    echo "Or modify the create_collections.py script to use a different key file."
    exit 1
fi

# Check for firebase-admin package
$PYTHON -c "import firebase_admin" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing firebase-admin package..."
    $PYTHON -m pip install firebase_admin
fi

# Run the collection creation script
echo "Creating Firebase collections..."
$PYTHON create_collections.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🔥 Firebase database setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Deploy Firestore security rules: firebase deploy --only firestore:rules"
    echo "2. Verify collections in the Firebase console: https://console.firebase.google.com"
    echo "3. Update your app configuration to use Firebase"
    echo ""
else
    echo "❌ Error occurred during setup. Please check the error messages above."
    exit 1
fi 