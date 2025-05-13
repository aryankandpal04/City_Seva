# Firebase Migration Guide for CitySeva WebApp

This document outlines the migration process from SQLite to Firebase for CitySeva WebApp.

## Migration Overview

The CitySeva WebApp now uses Firebase Firestore as its primary database and Firebase Storage for file storage. The migration includes:

1. Transferring all data from SQLite to Firebase
2. Updating the app to use Firebase for all CRUD operations
3. Ensuring backward compatibility for existing deployments

## Step 1: Install Required Dependencies

First, install the necessary Firebase dependencies:

```bash
pip install -r requirements-firebase.txt
```

This installs:
- firebase-admin
- google-cloud-firestore
- google-cloud-storage
- pyrebase4
- python-dotenv

## Step 2: Run the Migration Script

The migration script `migrate_to_firebase.py` transfers all data from SQLite to Firebase. Run this once to populate your Firebase instance:

```bash
python migrate_to_firebase.py
```

This will migrate:
- Users
- Categories
- Complaints
- Complaint Media (uploads)
- Complaint Updates
- Feedback
- Notifications
- Official Requests
- Audit Logs

The script generates an ID mapping file (`firebase_id_mapping.json`) to help trace the migration.

## Step 3: Update Environment Variables

Ensure your Firebase configuration is set in your environment variables or `cityseva.env` file:

```
# Firebase Configuration
FIREBASE_API_KEY=your-api-key
FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your-sender-id
FIREBASE_APP_ID=your-app-id
FIREBASE_MEASUREMENT_ID=your-measurement-id
FIREBASE_DATABASE_URL=https://your-project-id.firebaseio.com
FIREBASE_SERVICE_ACCOUNT_KEY=path/to/service-account-key.json

# Enable Firebase as primary data store
USE_FIREBASE=True
```

## Step 4: Update App Configuration

Run the update script to patch your application:

```bash
python update_app_to_firebase.py
```

This script will:
1. Update your app's `__init__.py` to import firebase_helpers
2. Configure the app to use Firebase by default
3. Add USE_FIREBASE=True to your environment file

## Step 5: Verify Firebase Collections

Run the verification script to ensure all required collections exist in your Firebase instance:

```bash
python verify_firebase_collections.py
```

This script checks for and creates sample documents in these collections:
- users
- categories
- complaints
- complaint_media
- complaint_updates
- feedbacks
- notifications
- official_requests
- audit_logs

## Step 6: Verify Migration Success

Test that the migration was successful by running:

```bash
python verify_firebase_migration.py
```

This will:
1. Check Firebase initialization
2. Verify all collections exist
3. Test basic CRUD operations
4. Generate sample reports

## Using Firebase Helpers

The new `firebase_helpers.py` module provides functions for all Firebase operations. Here are some examples:

```python
from app.firebase_helpers import (
    get_complaints, get_complaint, create_complaint, 
    update_complaint, delete_complaint
)

# Get all complaints with filters
complaints = get_complaints(
    limit=10, 
    status='pending', 
    category_id='some-category-id'
)

# Get a specific complaint with related data
complaint = get_complaint('complaint-id')

# Create a new complaint
new_complaint = create_complaint({
    'title': 'Test Complaint',
    'description': 'Description',
    'location': 'Test Location',
    'latitude': 12.345,
    'longitude': 67.890,
    'category_id': 'category-id',
    'user_id': 'user-id'
})

# Update a complaint
update_complaint('complaint-id', {
    'status': 'resolved'
})

# Delete a complaint and related data
delete_complaint('complaint-id')
```

See `firebase_routes_example.py` for complete examples of using Firebase in your Flask routes.

## Notes for Developers

### Backwards Compatibility

The app maintains backward compatibility with SQLite. If Firebase is disabled or not configured, the app will fall back to SQLite.

To disable Firebase and use SQLite, set:

```
USE_FIREBASE=False
```

### Password Migration

The migration does not transfer password hashes as Firebase Auth uses a different hashing method. Users will need to reset their passwords after migration.

### Media Files

Media files are migrated from the local filesystem to Firebase Storage. The original files remain untouched in the `app/static/uploads` directory.

### Error Handling

All Firebase operations include robust error handling and logging. Check your application logs for any issues.

## Troubleshooting

### Firebase Initialization Failed

If you encounter errors related to Firebase initialization:

1. Verify your service account key file exists and has proper permissions
2. Check that all Firebase environment variables are set correctly
3. Ensure your Firebase project has Firestore and Storage enabled

### Data Migration Issues

If you encounter issues during migration:

1. Check the console output for specific error messages
2. Verify network connectivity to Firebase services
3. Ensure your service account has proper permissions

### Post-Migration Data Verification

To verify your data was properly migrated:

1. Check the Firebase console to confirm collections contain data
2. Use the application to test common operations (view/create/update/delete)
3. Compare record counts between SQLite and Firebase 