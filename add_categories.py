import sqlite3

# Connect to the database (SQLite)
conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# Sample categories
categories = [
    ('Roads', 'Issues related to roads, potholes, and traffic signals', 'Public Works', 'fa-road'),
    ('Water Supply', 'Issues related to water supply, leakages, and quality', 'Water Department', 'fa-tint'),
    ('Electricity', 'Issues related to power outages, streetlights, and electrical hazards', 'Electricity Board', 'fa-bolt'),
    ('Garbage', 'Issues related to waste collection, dumps, and cleanups', 'Sanitation', 'fa-trash'),
    ('Parks & Playgrounds', 'Issues related to parks, playgrounds, and public spaces', 'Parks & Recreation', 'fa-tree'),
    ('Public Transport', 'Issues related to buses, bus stops, and public transport', 'Transport', 'fa-bus'),
    ('Stray Animals', 'Issues related to stray animals and animal control', 'Animal Control', 'fa-paw'),
    ('Others', 'Other civic issues not covered in other categories', 'General Administration', 'fa-exclamation-circle')
]

# Check if categories already exist
cursor.execute("SELECT COUNT(*) FROM category")
count = cursor.fetchone()[0]

if count > 0:
    print(f"Categories already exist ({count} found). No new categories added.")
else:
    # Insert categories
    for category in categories:
        cursor.execute(
            "INSERT INTO category (name, description, department, icon) VALUES (?, ?, ?, ?)",
            category
        )
    
    # Commit changes
    conn.commit()
    print(f"Successfully added {len(categories)} categories.")

# Close connection
conn.close() 