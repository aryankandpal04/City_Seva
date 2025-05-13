# Firebase Migration Checklist

This checklist will guide you through the complete process of migrating from SQLite to Firebase in CitySeva WebApp.

## Pre-Migration Preparation

- [ ] Install required dependencies:
  ```bash
  pip install -r requirements-firebase.txt
  ```

- [ ] Configure Firebase credentials:
  - [ ] Create a Firebase project in the [Firebase Console](https://console.firebase.google.com/)
  - [ ] Enable Firestore Database and Storage
  - [ ] Generate and download service account key
  - [ ] Place the service account key file in the project root as `cityseva-4d82b-firebase-adminsdk-fbsvc-a904038f62.json` (or update references to your file)

- [ ] Update `cityseva.env` with Firebase credentials:
  ```
  FIREBASE_API_KEY=your-api-key
  FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
  FIREBASE_PROJECT_ID=your-project-id
  FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
  FIREBASE_MESSAGING_SENDER_ID=your-sender-id
  FIREBASE_APP_ID=your-app-id
  FIREBASE_MEASUREMENT_ID=your-measurement-id
  FIREBASE_DATABASE_URL=https://your-project-id.firebaseio.com
  FIREBASE_SERVICE_ACCOUNT_KEY=path/to/service-account-key.json
  USE_FIREBASE=True
  ```

- [ ] Backup your SQLite database:
  ```bash
  cp instance/cityseva.db instance/cityseva.db.backup
  ```

## Migration Process

- [ ] Update app configuration:
  ```bash
  python update_app_to_firebase.py
  ```

- [ ] Verify Firebase collections:
  ```bash
  python verify_firebase_collections.py
  ```

- [ ] Run the migration script:
  ```bash
  python migrate_to_firebase.py
  ```

- [ ] Verify migration success:
  ```bash
  python verify_firebase_migration.py
  ```

## Post-Migration Verification

- [ ] Check Firebase Console:
  - [ ] Verify all collections contain data
  - [ ] Check document counts match SQLite tables

- [ ] Run application in development mode:
  ```bash
  python run.py
  ```

- [ ] Test core functionality:
  - [ ] User registration and login
  - [ ] Submitting complaints with attachments
  - [ ] Viewing and filtering complaints
  - [ ] Updating complaint status
  - [ ] Admin operations (category management, user management)

## Deployment Preparation

- [ ] Update production environment variables:
  - [ ] Add Firebase credentials to your production environment
  - [ ] Set `USE_FIREBASE=True` in production

- [ ] Deploy updated application
  ```bash
  # Use your regular deployment process
  ```

- [ ] Monitor application logs for Firebase-related errors

## Rollback Plan (If Needed)

If something goes wrong, you can roll back to SQLite:

- [ ] Set `USE_FIREBASE=False` in your environment variables
- [ ] Restore the original SQLite database if needed:
  ```bash
  cp instance/cityseva.db.backup instance/cityseva.db
  ```

## Final Steps

- [ ] Notify users about the migration (if applicable)
- [ ] Setup Firebase Authentication (optional future step)
- [ ] Configure Firebase Security Rules (required for production)
- [ ] Set up regular backups of Firebase data

## Resources

- [Firebase Documentation](https://firebase.google.com/docs)
- [Firebase Admin SDK Documentation](https://firebase.google.com/docs/admin/setup)
- [Firebase Firestore Documentation](https://firebase.google.com/docs/firestore)
- [Firebase Storage Documentation](https://firebase.google.com/docs/storage) 