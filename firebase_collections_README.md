# Firebase Collections Setup

This guide explains how to set up the required Firestore collections for CitySeva web application.

## Overview

The CitySeva application uses the following collections in Firebase Firestore:

1. **users** - Store user profile information
2. **categories** - Different categories of complaints
3. **complaints** - The main complaint records
4. **feedbacks** - User feedback about resolved complaints
5. **notifications** - System notifications for users
6. **official_requests** - Requests for official account privileges
7. **complaint_updates** - Updates/comments on complaints
8. **audit_logs** - System audit logs for security

## Setting Up Collections

You have two options to create these collections:

### Option 1: Using the Setup Script

1. Make sure you have your Firebase service account key file (JSON) downloaded from the Firebase Console
2. Place the key file in your project root directory as `cityseva-4d82b-firebase-adminsdk-fbsvc-a904038f62.json` or set the path using the environment variable:
   ```
   set FIREBASE_KEY_FILE=path/to/your/key.json  # Windows
   export FIREBASE_KEY_FILE=path/to/your/key.json  # Linux/Mac
   ```
3. Install required packages:
   ```
   pip install firebase-admin
   ```
4. Run the setup script:
   ```
   python create_collections.py
   ```

The script will create all collections with sample documents, which helps establish the correct schema.

### Option 2: Creating Collections Manually

In Firebase Firestore, collections are created implicitly when you add documents to them. To create collections manually:

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Navigate to Firestore Database
4. Click "Start Collection" and create each collection with the following names:
   - `complaints`
   - `feedbacks`
   - `notifications`
   - `official_requests`
   - `complaint_updates`
   - `audit_logs`
   - `users`
   - `categories`

5. For each collection, add a test document with the appropriate fields based on the schema in the script.

## Collection Schemas

### complaints
```json
{
  "title": "String",
  "description": "String",
  "user_id": "String (Reference to users)",
  "category_id": "String (Reference to categories)",
  "status": "String (pending/in_progress/resolved/rejected)",
  "priority": "String (low/medium/high/urgent)",
  "location": "String",
  "latitude": "Number",
  "longitude": "Number",
  "image_path": "String or null",
  "assigned_to_id": "String or null (Reference to users)",
  "assigned_at": "Timestamp or null",
  "resolved_at": "Timestamp or null",
  "created_at": "Timestamp",
  "updated_at": "Timestamp"
}
```

### feedbacks
```json
{
  "complaint_id": "String (Reference to complaints)",
  "user_id": "String (Reference to users)",
  "rating": "Number (1-5)",
  "comment": "String",
  "created_at": "Timestamp"
}
```

### notifications
```json
{
  "user_id": "String (Reference to users)",
  "title": "String",
  "message": "String",
  "is_read": "Boolean",
  "complaint_id": "String (Reference to complaints)",
  "category": "String",
  "link": "String",
  "created_at": "Timestamp"
}
```

### official_requests
```json
{
  "user_id": "String (Reference to users)",
  "department": "String",
  "position": "String",
  "employee_id": "String",
  "office_phone": "String",
  "justification": "String",
  "status": "String (pending/approved/rejected)",
  "reviewed_by": "String or null (Reference to users)",
  "reviewed_at": "Timestamp or null",
  "review_notes": "String or null",
  "created_at": "Timestamp"
}
```

## Collection Relationships

The collections relate to each other as shown in the diagram below:

```
            ┌─────────────┐
            │  categories │
            └─────┬───────┘
                  │
                  │
┌─────────┐    ┌──▼────────┐    ┌─────────────┐
│ feedbacks│◄───┤ complaints ├───►audit_logs   │
└─────────┘    └──┬─────┬───┘    └─────────────┘
                  │     │
                  │     │         ┌─────────────┐
                  │     └─────────► notifications│◄──┐
                  │               └──────────────┘   │
                  │                                  │
┌────────────────┐│               ┌─────────────┐   │
│complaint_updates◄───────────────┤   users     ├───┘
└────────────────┘                └──────┬──────┘
                                         │
                                         │
                                  ┌──────▼──────┐
                                  │official_requests│
                                  └───────────────┘
``` 