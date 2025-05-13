"""
Simple Firebase Export - Dumps SQLite data to JSON files for import into Firebase
"""
import os
import sys
import json
import sqlite3
import datetime

# Add the app directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def convert_datetime(dt):
    """Convert datetime to string"""
    if dt is None:
        return None
    if isinstance(dt, datetime.datetime):
        return dt.isoformat()
    return dt

def query_sqlite_table(conn, table_name):
    """Get all rows from a SQLite table"""
    cursor = conn.cursor()
    
    # Get all rows
    cursor.execute(f"SELECT * FROM {table_name};")
    rows = cursor.fetchall()
    
    # Convert to list of dicts
    result = []
    for row in rows:
        row_dict = {key: row[key] for key in row.keys()}
        # Convert datetime strings to isoformat
        for key, value in row_dict.items():
            if isinstance(value, str) and (
                'date' in key.lower() or 
                'time' in key.lower() or 
                key in ['created_at', 'updated_at', 'resolved_at', 'assigned_at', 'last_login', 'reviewed_at']
            ):
                try:
                    dt = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
                    row_dict[key] = dt.isoformat()
                except (ValueError, TypeError):
                    pass
        result.append(row_dict)
    
    return result

def export_all_tables():
    """Export all SQLite tables to JSON files"""
    # Define output directory
    output_dir = 'firebase_export'
    os.makedirs(output_dir, exist_ok=True)
    
    # Open SQLite database
    db_path = os.path.join('instance', 'cityseva.db')
    if not os.path.exists(db_path):
        print(f"Error: SQLite database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall()]
    
    print(f"Found {len(tables)} tables in SQLite database: {tables}")
    
    # Export each table to JSON
    for table in tables:
        try:
            data = query_sqlite_table(conn, table)
            output_file = os.path.join(output_dir, f"{table}.json")
            
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            print(f"Exported {len(data)} records from '{table}' to {output_file}")
        except Exception as e:
            print(f"Error exporting table '{table}': {e}")
    
    # Close connection
    conn.close()
    
    print("\nExport complete!")
    print(f"JSON files are saved in the '{output_dir}' directory")
    print("These files can be imported into Firebase using the Firebase Console or Firebase Admin SDK")
    
    return True

def generate_import_script():
    """Generate a script to import the JSON files into Firebase"""
    import_script = """
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Import directory
import_dir = 'firebase_export'

# Function to import a JSON file to a Firestore collection
def import_collection(file_path, collection_name):
    print(f"Importing {file_path} to {collection_name}...")
    
    # Read JSON file
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Skip empty collections
    if not data:
        print(f"No data in {file_path}. Skipping.")
        return 0
    
    # Import data to Firestore
    collection_ref = db.collection(collection_name)
    count = 0
    
    for item in data:
        # Use the original ID if available
        if 'id' in item:
            item_id = str(item['id'])
            collection_ref.document(item_id).set(item)
        else:
            # Generate a new document ID
            collection_ref.add(item)
        count += 1
    
    print(f"Successfully imported {count} documents to {collection_name}")
    return count

# Import each collection
total_imported = 0
collections = [f for f in os.listdir(import_dir) if f.endswith('.json')]

for collection_file in collections:
    collection_name = os.path.splitext(collection_file)[0]
    file_path = os.path.join(import_dir, collection_file)
    count = import_collection(file_path, collection_name)
    total_imported += count

print(f"\\nImport complete! Imported {total_imported} documents to Firestore")
    """
    
    # Write the import script to a file
    with open('import_to_firebase.py', 'w') as f:
        f.write(import_script)
    
    print("\nGenerated import script: import_to_firebase.py")
    print("To import the data to Firebase:")
    print("1. Download a new service account key from Firebase Console")
    print("2. Save it as 'firebase-service-account.json'")
    print("3. Run: python import_to_firebase.py")

if __name__ == "__main__":
    print("This script will export all tables from SQLite to JSON files")
    print("These files can be imported into Firebase")
    
    export_all_tables()
    generate_import_script() 