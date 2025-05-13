# Simple Firebase JWT Fix

You're seeing this error because your Firebase service account key is invalid or corrupted:

```
Error: Getting metadata from plugin failed with error: ('invalid_grant: Invalid JWT Signature.')
```

## Follow these steps to fix it:

### Step 1: Generate a new service account key

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project (cityseva-4d82b)
3. Click the gear icon (⚙️) for Project Settings
4. Go to the "Service accounts" tab
5. Click "Generate new private key" button
6. Save the downloaded JSON file to your project directory (e.g., `firebase-key.json`)

### Step 2: Update your environment file

Open your `cityseva.env` file and update the service account key line:

```
FIREBASE_SERVICE_ACCOUNT_KEY=firebase-key.json
```

Make sure the path is correct. You can use a relative path or absolute path.

### Step 3: Check Firebase settings

Ensure these other settings are correct in your `cityseva.env` file:

```
USE_FIREBASE=True
FIREBASE_PROJECT_ID=cityseva-4d82b
```

### Step 4: Try a simple test

Run this short script to verify your credentials:

```python
python fix_firebase_key.py
```

If it shows "Service account key is valid", your service account key is fixed!

### Step 5: Restart your application

After fixing the service account key, restart your application for the changes to take effect.

## What happened?

The JWT signature error usually happens because:
1. Your service account key was revoked or expired
2. The key file became corrupted
3. The JSON format in the environment variable is incorrect

Generating a new key is the simplest solution. 