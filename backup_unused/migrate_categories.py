"""
Migrate Categories from SQLite to Firebase
"""
import os
import sys
import json
import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate("cityseva-4d82b-firebase-adminsdk-fbsvc-a904038f62.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Connect to SQLite database
sqlite_db_path = os.path.join('instance', 'cityseva.db')
conn = sqlite3.connect(sqlite_db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

def migrate_categories():
    """Migrate categories from SQLite to Firebase"""
    print("Migrating categories...")
    
    # Get all categories from SQLite
    cursor.execute("SELECT * FROM categories;")
    categories = cursor.fetchall()
    
    # Convert to list of dictionaries
    categories_list = []
    for category in categories:
        category_dict = {key: category[key] for key in category.keys()}
        categories_list.append(category_dict)
    
    # Print categories for verification
    print(f"Found {len(categories_list)} categories in SQLite database:")
    for category in categories_list:
        print(f"  - {category['id']}: {category['name']} ({category['department']})")
    
    # Upload categories to Firebase
    categories_ref = db.collection('categories')
    
    # First check if the collection is empty
    docs = categories_ref.limit(1).get()
    if len(list(docs)) > 0:
        if input("Categories already exist in Firebase. Replace them? (y/n): ").lower() != 'y':
            print("Migration cancelled.")
            return
        
        # Delete existing documents
        print("Deleting existing categories...")
        existing_docs = categories_ref.get()
        for doc in existing_docs:
            doc.reference.delete()
    
    # Add categories with original ID as document ID
    for category in categories_list:
        doc_id = str(category['id'])
        categories_ref.document(doc_id).set(category)
        print(f"Added category: {category['name']}")
    
    print(f"Successfully migrated {len(categories_list)} categories to Firebase!")

def main():
    """Main function"""
    try:
        migrate_categories()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close SQLite connection
        conn.close()

if __name__ == "__main__":
    main() 