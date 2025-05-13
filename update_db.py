import sqlite3
import os

# Database file path
db_file = 'instance/cityseva.db'

print(f"Using database file: {db_file}")

# Connect to the database
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

try:
    # Check if media_path column exists
    cursor.execute("PRAGMA table_info(complaints)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'media_path' not in columns:
        print("Adding media_path column...")
        cursor.execute("ALTER TABLE complaints ADD COLUMN media_path VARCHAR(256);")
    else:
        print("media_path column already exists.")
    
    if 'media_type' not in columns:
        print("Adding media_type column...")
        cursor.execute("ALTER TABLE complaints ADD COLUMN media_type VARCHAR(10);")
    else:
        print("media_type column already exists.")
    
    # Commit changes
    conn.commit()
    print("Database schema updated successfully!")
    
except Exception as e:
    print(f"Error updating database schema: {e}")
    conn.rollback()
finally:
    conn.close() 