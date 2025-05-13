import os
import sys
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from flask import Flask
from app import db, create_app
from app.models import User, Category, Complaint, ComplaintUpdate, Feedback, Notification, AuditLog, OfficialRequest, ComplaintMedia

# Initialize the Flask application
app = create_app('development')

# Sample data
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

users = [
    {
        'first_name': 'Admin',
        'last_name': 'User',
        'username': 'admin123',
        'email': 'admin@cityseva.com',
        'password': 'Admin@123',
        'role': 'admin',
        'phone': '1234567890',
        'address': 'Admin Office, City Center',
    },
    {
        'first_name': 'Water',
        'last_name': 'Official',
        'username': 'water_official',
        'email': 'water@cityseva.com',
        'password': 'Water@123',
        'role': 'official',
        'department': 'Water Department',
        'phone': '2345678901',
        'address': 'Water Department Office, City Center',
    },
    {
        'first_name': 'Road',
        'last_name': 'Official',
        'username': 'road_official',
        'email': 'road@cityseva.com',
        'password': 'Road@123',
        'role': 'official',
        'department': 'Public Works',
        'phone': '3456789012',
        'address': 'Public Works Office, City Center',
    },
    {
        'first_name': 'Electricity',
        'last_name': 'Official',
        'username': 'electricity_official',
        'email': 'electricity@cityseva.com',
        'password': 'Electricity@123',
        'role': 'official',
        'department': 'Electricity Board',
        'phone': '4567890123',
        'address': 'Electricity Board Office, City Center',
    },
    {
        'first_name': 'Sanitation',
        'last_name': 'Official',
        'username': 'sanitation_official',
        'email': 'sanitation@cityseva.com',
        'password': 'Sanitation@123',
        'role': 'official',
        'department': 'Sanitation',
        'phone': '5678901234',
        'address': 'Sanitation Department Office, City Center',
    },
    {
        'first_name': 'Parks',
        'last_name': 'Official',
        'username': 'parks_official',
        'email': 'parks@cityseva.com',
        'password': 'Parks@123',
        'role': 'official',
        'department': 'Parks & Recreation',
        'phone': '6789012345',
        'address': 'Parks & Recreation Office, City Center',
    },
    {
        'first_name': 'Transport',
        'last_name': 'Official',
        'username': 'transport_official',
        'email': 'transport@cityseva.com',
        'password': 'Transport@123',
        'role': 'official',
        'department': 'Transport',
        'phone': '7890123456',
        'address': 'Transport Department Office, City Center',
    },
    {
        'first_name': 'Animal',
        'last_name': 'Control',
        'username': 'animal_official',
        'email': 'animal@cityseva.com',
        'password': 'Animal@123',
        'role': 'official',
        'department': 'Animal Control',
        'phone': '8901234567',
        'address': 'Animal Control Department Office, City Center',
    },
    {
        'first_name': 'General',
        'last_name': 'Admin',
        'username': 'general_official',
        'email': 'general@cityseva.com',
        'password': 'General@123',
        'role': 'official',
        'department': 'General Administration',
        'phone': '9012345678',
        'address': 'General Administration Office, City Center',
    },
    {
        'first_name': 'John',
        'last_name': 'Doe',
        'username': 'john_doe',
        'email': 'john@example.com',
        'password': 'John@123',
        'role': 'citizen',
        'phone': '9567890123',
        'address': '123 Main Street, Downtown',
    },
    {
        'first_name': 'Jane',
        'last_name': 'Smith',
        'username': 'jane_smith',
        'email': 'jane@example.com',
        'password': 'Jane@123',
        'role': 'citizen',
        'phone': '0678901234',
        'address': '456 Oak Avenue, Uptown',
    }
]

locations = [
    'Main Street, Downtown',
    'Park Avenue, Central Park',
    'Broadway Street, Theater District',
    'Lake View Road, Near City Lake',
    'Market Street, Shopping District',
    'University Road, Campus Area',
    'Industrial Avenue, Factory Zone',
    'Residential Block, Green Hills',
    'Station Road, Near Central Station',
    'Hospital Road, Medical District'
]

complaint_titles = [
    'Pothole on the road causing accidents',
    'Garbage not collected for a week',
    'Streetlight not working for days',
    'Water leakage from main pipeline',
    'Stray dogs creating nuisance',
    'Broken swings in the park',
    'Sewage overflow on the street',
    'Public toilet in unsanitary condition',
    'Bus stop shelter damaged',
    'Trees not pruned causing hazard'
]

complaint_descriptions = [
    'There is a large pothole on the road that has been causing accidents. Please fix it as soon as possible.',
    'The garbage has not been collected for over a week and is causing bad odor in the area.',
    'The streetlight outside my house has not been working for several days, causing safety concerns at night.',
    'There is a significant water leakage from the main pipeline, wasting a lot of water and damaging the road.',
    'A group of stray dogs in our area is creating nuisance and posing threat to children and elderly.',
    'The swings in the community park are broken and pose a danger to children. Please repair or replace them.',
    'There is sewage overflow on our street causing health hazards. Immediate action is required.',
    'The public toilet near the market is in extremely unsanitary condition and needs cleaning and maintenance.',
    'The bus stop shelter is damaged due to recent storms and needs repair to protect commuters from rain and sun.',
    'The trees along our street have not been pruned for months and branches are hanging dangerously low over the road.'
]

update_comments = [
    'Complaint received and registered',
    'Assigned to the concerned department',
    'Inspection scheduled',
    'Inspection completed, work order generated',
    'Work in progress',
    'Material procurement in process',
    'Temporarily fixed, permanent solution pending',
    'Issue resolved successfully',
    'Verified and closed',
    'No action required as per inspection'
]

feedback_comments = [
    'Very satisfied with the quick resolution',
    'Good service but took longer than expected',
    'Satisfactory resolution but communication could be improved',
    'Issue fixed but quality of work is average',
    'Excellent service and prompt action'
]

notification_titles = [
    'Complaint Update',
    'Complaint Assigned',
    'Resolution Confirmation',
    'Feedback Required',
    'Official Response',
    'Complaint Status Change',
    'Priority Update',
    'New Assignment',
    'Department Transfer',
    'Service Announcement'
]

notification_messages = [
    'Your complaint has been updated with a new status.',
    'Your complaint has been assigned to an official.',
    'Please confirm if your complaint has been resolved to your satisfaction.',
    'Please provide feedback on the resolution of your complaint.',
    'An official has responded to your complaint.',
    'The status of your complaint has been changed.',
    'The priority of your complaint has been updated.',
    'You have been assigned a new complaint to handle.',
    'Your complaint has been transferred to another department.',
    'There will be a scheduled maintenance of our services.'
]

priorities = ['low', 'medium', 'high', 'urgent']
statuses = ['pending', 'in_progress', 'resolved', 'rejected']

def create_sample_data():
    """Create sample data for the CitySeva application"""
    with app.app_context():
        # Create categories
        print("Creating categories...")
        for category_data in categories:
            category = Category(
                name=category_data['name'],
                description=category_data['description'],
                department=category_data['department'],
                icon=category_data['icon']
            )
            db.session.add(category)
        db.session.commit()
        
        # Create users
        print("Creating users...")
        created_users = []
        for user_data in users:
            user = User(
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                username=user_data['username'],
                email=user_data['email'],
                phone=user_data['phone'],
                address=user_data['address'],
                role=user_data['role'],
                department=user_data.get('department'),
                password_hash=generate_password_hash(user_data['password']),
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 90))
            )
            db.session.add(user)
            created_users.append(user)
        db.session.commit()
        
        # Get citizens and officials
        citizens = [user for user in created_users if user.role == 'citizen']
        officials = [user for user in created_users if user.role == 'official']
        
        # Create complaints
        print("Creating complaints and updates...")
        created_complaints = []
        for i in range(20):  # Create 20 sample complaints
            # Select random data
            user = random.choice(citizens)
            category = Category.query.filter_by(name=random.choice([c['name'] for c in categories])).first()
            title = random.choice(complaint_titles)
            description = random.choice(complaint_descriptions)
            location = random.choice(locations)
            priority = random.choice(priorities)
            
            # Random dates
            days_ago = random.randint(1, 60)
            created_at = datetime.utcnow() - timedelta(days=days_ago)
            
            # Create the complaint
            complaint = Complaint(
                title=f"{title} - Sample #{i+1}",
                description=description,
                location=location,
                latitude=round(random.uniform(18.9, 19.2), 6),
                longitude=round(random.uniform(72.8, 73.1), 6),
                category_id=category.id,
                user_id=user.id,
                priority=priority,
                status=random.choice(statuses),
                created_at=created_at,
                updated_at=created_at
            )
            
            # If status is in_progress or resolved, assign to an official
            if complaint.status in ['in_progress', 'resolved']:
                # Try to find an official from the same department
                dept_officials = [o for o in officials if o.department == category.department]
                if dept_officials:
                    assigned_to = random.choice(dept_officials)
                else:
                    assigned_to = random.choice(officials)
                
                complaint.assigned_to_id = assigned_to.id
                complaint.assigned_at = created_at + timedelta(days=random.randint(1, 3))
            
            # If status is resolved, set resolved_at date
            if complaint.status == 'resolved':
                complaint.resolved_at = created_at + timedelta(days=random.randint(4, 10))
            
            db.session.add(complaint)
            db.session.commit()  # Commit to get the complaint ID
            created_complaints.append(complaint)
            
            # Create updates for this complaint
            num_updates = random.randint(1, 5)
            
            # Initial update (submission)
            update = ComplaintUpdate(
                complaint_id=complaint.id,
                user_id=user.id,
                status='pending',
                comment='Complaint submitted',
                created_at=created_at
            )
            db.session.add(update)
            
            if num_updates > 1 and complaint.status != 'pending':
                # Create progression updates
                current_status = 'pending'
                current_date = created_at
                
                for j in range(1, num_updates):
                    # Progress through statuses
                    if current_status == 'pending':
                        current_status = 'in_progress'
                    elif current_status == 'in_progress' and complaint.status in ['resolved', 'rejected']:
                        current_status = complaint.status
                    
                    # Add some days
                    current_date += timedelta(days=random.randint(1, 3))
                    
                    # Create the update
                    update_user = random.choice(officials) if current_status != 'pending' else user
                    update = ComplaintUpdate(
                        complaint_id=complaint.id,
                        user_id=update_user.id,
                        status=current_status,
                        comment=random.choice(update_comments),
                        created_at=current_date
                    )
                    db.session.add(update)
            
            # Create feedback for resolved complaints
            if complaint.status == 'resolved' and random.random() < 0.7:  # 70% chance
                feedback = Feedback(
                    complaint_id=complaint.id,
                    user_id=user.id,
                    rating=random.randint(1, 5),
                    comment=random.choice(feedback_comments),
                    created_at=complaint.resolved_at + timedelta(days=random.randint(1, 5))
                )
                db.session.add(feedback)
        
        # Commit all changes
        db.session.commit()
        print("Sample data creation completed!")
        print(f"Created {len(categories)} categories")
        print(f"Created {len(created_users)} users")
        print(f"Created {len(created_complaints)} complaints with updates and feedback")

if __name__ == '__main__':
    # Check if database should be reset
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        with app.app_context():
            # Drop all tables
            db.drop_all()
            print("Database tables dropped.")
            # Create tables
            db.create_all()
            print("Database tables created.")
    
    # Create sample data
    create_sample_data() 