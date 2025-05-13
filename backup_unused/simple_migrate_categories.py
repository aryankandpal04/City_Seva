"""
Simple Categories Migration to Firebase
"""
import os
import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore

# Path to your service account key
KEY_PATH = "cityseva-4d82b-firebase-adminsdk-fbsvc-a904038f62.json"

# Initialize Firebase
cred = credentials.Certificate(KEY_PATH)
try:
    firebase_admin.initialize_app(cred)
except ValueError:
    # App already initialized
    pass
db = firestore.client()

# Connect to SQLite
db_path = os.path.join('instance', 'cityseva.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Get categories from SQLite
cursor = conn.cursor()
cursor.execute("SELECT * FROM categories")
categories = cursor.fetchall()

print(f"Found {len(categories)} categories in SQLite database")

# Add each category to Firebase
count = 0
for category in categories:
    # Convert row to dict
    cat_dict = {}
    for key in category.keys():
        cat_dict[key] = category[key]
    
    # Use the original ID as document ID
    doc_id = str(cat_dict['id'])
    
    # Add to Firebase
    db.collection('categories').document(doc_id).set(cat_dict)
    count += 1
    print(f"Added category: {cat_dict['name']}")

# Close SQLite connection
conn.close()

print(f"\nSuccessfully migrated {count} categories to Firebase!")
print("Check your Firebase console to verify the categories collection.") 