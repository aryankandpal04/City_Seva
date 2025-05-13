# Manual Firebase Collection Setup Guide

Since we're having issues with automated scripts, follow these steps to manually set up your Firebase collections through the Firebase Console:

## Step 1: Access Firebase Console

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project "cityseva-4d82b"

## Step 2: Navigate to Firestore Database

1. In the left sidebar, click on "Build" and then select "Firestore Database"
2. If you see a "Create database" button, click it and follow the setup wizard
   - Choose "Start in production mode"
   - Select a database location closest to your users
   - Click "Enable"

## Step 3: Create Collections

For each of the following collection names, follow these steps:

1. Click the "Start collection" or "Add collection" button
2. Enter the collection ID exactly as shown below
3. Click "Next"
4. Add a first document with Auto-ID (leave the ID field auto-generated)
5. Add a single field: `placeholder` (type: boolean) with value `true`
6. Click "Save" to create the collection and document

Create these collections one by one:

- `users`
- `categories`
- `complaints`
- `complaint_updates`
- `feedbacks`
- `audit_logs`
- `notifications`
- `official_requests`
- `complaint_media`

## Step 4: Verify Collections

After creating all collections, refresh the page and check that all 9 collections appear in the list on the left side of the Firestore Database page.

## Step 5: Update Environment Configuration

Make sure your `cityseva.env` file has the following settings:

```
USE_FIREBASE=True
```

## Step 6: Test Your Application

Start your application and verify that it can now access the Firebase collections correctly.

## Step 7: Import Data (Optional)

If you want to import your SQLite data into Firebase:

1. Go back to your exported JSON files in the `firebase_export` directory
2. For each collection you want to populate with data:
   - Open the Firebase Console
   - Click on the collection
   - Click "Add document"
   - Set the Document ID to match the original ID
   - Add fields matching those in your JSON file
   - Click "Save"

You can also use Firebase's import/export functionality for bulk operations through the Firebase Console. 