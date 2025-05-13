# CitySeva Firebase Database Schema

This document describes the Firebase Firestore database schema used in the CitySeva application.

## Collections Overview

The CitySeva application uses the following Firestore collections:

1. **users** - User accounts and profiles
2. **categories** - Complaint categories
3. **complaints** - Citizen complaints
4. **feedbacks** - User feedback on resolved complaints
5. **notifications** - User notifications
6. **official_requests** - Requests for official accounts
7. **complaint_updates** - Updates to complaint status
8. **audit_logs** - System audit logs

## Collection Schemas

### Users Collection

**Collection Name:** `users`

| Field | Type | Description |
|-------|------|-------------|
| email | String | User's email address (unique) |
| first_name | String | User's first name |
| last_name | String | User's last name |
| username | String | User's chosen username (unique) |
| role | String | User's role (citizen, official, admin) |
| is_active | Boolean | Whether the user account is active |
| department | String | Department (for officials only) |
| phone | String | User's phone number (optional) |
| address | String | User's address (optional) |
| created_at | Timestamp | When the user account was created |
| updated_at | Timestamp | When the user account was last updated |

### Categories Collection

**Collection Name:** `categories`

| Field | Type | Description |
|-------|------|-------------|
| name | String | Category name (e.g., "Road Maintenance") |
| description | String | Description of issues in this category |
| department | String | Government department responsible |
| icon | String | Font Awesome icon name for the category |
| created_at | Timestamp | When the category was created |

### Complaints Collection

**Collection Name:** `complaints`

| Field | Type | Description |
|-------|------|-------------|
| title | String | Complaint title |
| description | String | Detailed description of the issue |
| user_id | String | ID of the user who submitted the complaint |
| category_id | String | ID of the complaint category |
| status | String | Current status (pending, in_progress, resolved, rejected) |
| priority | String | Priority level (low, medium, high, urgent) |
| location | String | Text description of the location |
| latitude | Number | GPS latitude coordinate |
| longitude | Number | GPS longitude coordinate |
| image_path | String | Path to uploaded image (optional) |
| assigned_to_id | String | ID of the official assigned to the complaint |
| assigned_at | Timestamp | When the complaint was assigned |
| resolved_at | Timestamp | When the complaint was resolved |
| created_at | Timestamp | When the complaint was created |
| updated_at | Timestamp | When the complaint was last updated |

### Feedbacks Collection

**Collection Name:** `feedbacks`

| Field | Type | Description |
|-------|------|-------------|
| complaint_id | String | ID of the complaint being rated |
| user_id | String | ID of the user giving feedback |
| rating | Number | Rating score (1-5) |
| comment | String | User's comment about the resolution |
| created_at | Timestamp | When the feedback was submitted |

### Notifications Collection

**Collection Name:** `notifications`

| Field | Type | Description |
|-------|------|-------------|
| user_id | String | ID of the user receiving the notification |
| title | String | Notification title |
| message | String | Notification message |
| is_read | Boolean | Whether the notification has been read |
| complaint_id | String | Related complaint ID (optional) |
| category | String | Notification type (e.g., status_update) |
| link | String | URL to relevant page in the app |
| created_at | Timestamp | When the notification was created |

### Official Requests Collection

**Collection Name:** `official_requests`

| Field | Type | Description |
|-------|------|-------------|
| user_id | String | ID of the user requesting official status |
| department | String | Department they work for |
| position | String | Job position |
| employee_id | String | Employee ID number |
| office_phone | String | Office phone number |
| justification | String | Reason for requesting official status |
| status | String | Request status (pending, approved, rejected) |
| reviewed_by | String | ID of admin who reviewed the request |
| reviewed_at | Timestamp | When the request was reviewed |
| review_notes | String | Admin notes on the decision |
| created_at | Timestamp | When the request was submitted |

### Complaint Updates Collection

**Collection Name:** `complaint_updates`

| Field | Type | Description |
|-------|------|-------------|
| complaint_id | String | ID of the complaint being updated |
| user_id | String | ID of the user making the update |
| status | String | New status of the complaint |
| comment | String | Comment explaining the update |
| created_at | Timestamp | When the update was made |

### Audit Logs Collection

**Collection Name:** `audit_logs`

| Field | Type | Description |
|-------|------|-------------|
| user_id | String | ID of the user who performed the action |
| action | String | Action performed (create, update, delete) |
| resource_type | String | Type of resource affected (user, complaint, etc.) |
| resource_id | String | ID of the affected resource |
| details | String | Detailed description of the action |
| ip_address | String | IP address of the user |
| created_at | Timestamp | When the action occurred |

## Security Considerations

* The Firestore security rules are defined in `firestore.rules`.
* Only authenticated users can create complaints.
* Only admins and officials can update complaint status.
* Regular citizens can only update their own complaints if the status is still "pending".
* Only admins can delete data from the database.

## Data Migrations

* Use the `create_collections.py` script to initialize the database collections.
* Run `setup_firebase_db.bat` (Windows) or `setup_firebase_db.sh` (Mac/Linux) to set up all collections at once.

## Relationships

* **Users to Complaints**: One-to-many (a user can have multiple complaints)
* **Categories to Complaints**: One-to-many (a category can have multiple complaints)
* **Complaints to Updates**: One-to-many (a complaint can have multiple status updates)
* **Complaints to Feedbacks**: One-to-one (a complaint can have one feedback)
* **Users to Notifications**: One-to-many (a user can have multiple notifications)
* **Users to Official Requests**: One-to-many (a user can make multiple official requests, although typically just one) 