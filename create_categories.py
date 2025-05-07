from app import db, create_app
from app.models import Category

# Initialize the Flask application
app = create_app('development')

# Sample categories
categories = [
    {
        'name': 'Roads',
        'description': 'Issues related to roads, potholes, and traffic signals',
        'department': 'Public Works',
        'icon': 'fa-road'
    },
    {
        'name': 'Water Supply',
        'description': 'Issues related to water supply, leakages, and quality',
        'department': 'Water Department',
        'icon': 'fa-tint'
    },
    {
        'name': 'Electricity',
        'description': 'Issues related to power outages, streetlights, and electrical hazards',
        'department': 'Electricity Board',
        'icon': 'fa-bolt'
    },
    {
        'name': 'Garbage',
        'description': 'Issues related to waste collection, dumps, and cleanups',
        'department': 'Sanitation',
        'icon': 'fa-trash'
    },
    {
        'name': 'Parks & Playgrounds',
        'description': 'Issues related to parks, playgrounds, and public spaces',
        'department': 'Parks & Recreation',
        'icon': 'fa-tree'
    },
    {
        'name': 'Public Transport',
        'description': 'Issues related to buses, bus stops, and public transport',
        'department': 'Transport',
        'icon': 'fa-bus'
    },
    {
        'name': 'Stray Animals',
        'description': 'Issues related to stray animals and animal control',
        'department': 'Animal Control',
        'icon': 'fa-paw'
    },
    {
        'name': 'Others',
        'description': 'Other civic issues not covered in other categories',
        'department': 'General Administration',
        'icon': 'fa-exclamation-circle'
    }
]

def add_categories():
    """Add categories to the database"""
    with app.app_context():
        # Check if categories already exist
        existing_count = Category.query.count()
        if existing_count > 0:
            print(f"Categories already exist ({existing_count} found). No new categories added.")
            return
            
        # Create categories
        print("Adding categories...")
        for category_data in categories:
            category = Category(
                name=category_data['name'],
                description=category_data['description'],
                department=category_data['department'],
                icon=category_data['icon']
            )
            db.session.add(category)
        
        # Commit changes
        db.session.commit()
        print(f"Successfully added {len(categories)} categories.")

if __name__ == '__main__':
    add_categories() 