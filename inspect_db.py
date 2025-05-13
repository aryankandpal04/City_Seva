"""
Inspect SQLite database structure and content
"""
import os
import sys
import sqlite3
from pprint import pprint

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Connect to the database
db_path = os.path.join('instance', 'cityseva.db')
print(f"Connecting to database at: {os.path.abspath(db_path)}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("\nTables in the database:")
for table in tables:
    print(f"- {table[0]}")

# For each table, get schema and count
print("\nTable schemas and row counts:")
for table in tables:
    table_name = table[0]
    print(f"\n=== {table_name} ===")
    
    # Get schema
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    print("Schema:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cursor.fetchone()[0]
    print(f"Row count: {count}")
    
    # Show sample data (up to 5 rows)
    if count > 0:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
        rows = cursor.fetchall()
        print("Sample data:")
        for row in rows:
            print(f"  {row}")

# Close connection
conn.close()
print("\nDatabase inspection complete!") 