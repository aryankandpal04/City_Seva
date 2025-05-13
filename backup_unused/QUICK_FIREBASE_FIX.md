# Quick Firebase Fix

Follow these steps to immediately fix your Firebase collections:

## Step 1: Download a new Firebase Service Account Key

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Click the gear icon (⚙️) for Project Settings
4. Go to the "Service accounts" tab
5. Click "Generate new private key" button
6. Save the downloaded JSON file as `firebase-service-account.json` in your project root

## Step 2: Run the force create script

Run this command to force create all the required collections:

```
python force_create_collections.py
```

This script will create all 9 collections in your Firebase database, even if they already exist.

## Step 3: Verify in Firebase Console

1. Go to your Firebase Console
2. Navigate to Firestore Database
3. Check that all these collections now exist:
   - users
   - categories
   - complaints
   - complaint_updates
   - feedbacks
   - audit_logs
   - notifications
   - official_requests
   - complaint_media

## Step 4: Make sure your app uses Firebase

Make sure your `cityseva.env` file has:

```
USE_FIREBASE=True
FIREBASE_SERVICE_ACCOUNT_KEY=firebase-service-account.json
```

Then restart your application.

## Troubleshooting

If you still have issues:
1. Check Firebase Console to confirm the collections exist
2. Check your project's Firebase configuration
3. Look at any error messages in your app logs 