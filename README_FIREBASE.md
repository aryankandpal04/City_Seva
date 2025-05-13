# Migrating from SQLite to Firebase in CitySeva

This document provides instructions for migrating the CitySeva application from SQLite to Firebase.

## Prerequisites

1. A Google account
2. Firebase project created in the [Firebase Console](https://console.firebase.google.com/)
3. Python 3.6+ and pip

## Setup Steps

### 1. Create a Firebase Project

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project"
3. Enter a project name (e.g., "CitySeva")
4. Follow the setup wizard to complete the project creation

### 2. Set Up Firestore Database

1. In your Firebase project, go to "Firestore Database" in the left sidebar
2. Click "Create database"
3. Choose "Start in production mode" and select your region
4. Click "Enable"

### 3. Set Up Firebase Storage

1. In your Firebase project, go to "Storage" in the left sidebar
2. Click "Get started"
3. Choose your security rules and click "Next"
4. Select your region and click "Done"

### 4. Generate a Service Account Key

1. In your Firebase project, go to "Project settings" (gear icon)
2. Go to the "Service accounts" tab
3. Click "Generate new private key"
4. Save the JSON file securely

### 5. Update Application Configuration

1. Add the Firebase configuration to your `cityseva.env` file:

```
FIREBASE_API_KEY=your-api-key
FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your-sender-id
FIREBASE_APP_ID=your-app-id
FIREBASE_MEASUREMENT_ID=your-measurement-id
FIREBASE_DATABASE_URL=https://your-project-id.firebaseio.com
```

2. Place the service account key file in your project directory or provide the path in your environment variables:

```
FIREBASE_SERVICE_ACCOUNT_KEY=/path/to/your/serviceAccountKey.json
```

Alternatively, you can set the environment variable to the JSON content directly.

### 6. Install Required Packages

```bash
pip install firebase-admin
```

### 7. Migrate Data from SQLite to Firebase

Run the provided migration script:

```bash
python migrate_to_firebase.py
```

This will transfer all existing data from your SQLite database to Firebase Firestore.

## File Structure Changes

The migration adds the following new files:

- `app/firebase_db.py`: Handles Firebase database connections and operations
- `migrate_to_firebase.py`: Migrates data from SQLite to Firebase

## Usage

After setting up Firebase, the application will automatically use Firebase if the configuration is present. If not, it will fall back to using SQLite.

## Security Considerations

1. **Never commit your service account key to version control**
2. Set appropriate security rules in your Firestore and Storage consoles
3. Consider using Firebase Authentication for more secure user management

## Troubleshooting

- If you encounter initialization issues, check that your service account key is correctly formatted and accessible
- Verify that your Firebase project has Firestore and Storage enabled
- Ensure all required environment variables are set correctly
- Check application logs for detailed error messages 