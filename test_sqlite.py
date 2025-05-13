import os
import unittest
from flask import current_app
from app import create_app, db
from app.models import User, Category, Complaint

class SQLiteTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Add some test data
        admin = User(
            username='admin_test',
            email='admin_test@example.com',
            password='Admin@123',
            first_name='Admin',
            last_name='Test',
            role='admin'
        )
        
        category = Category(
            name='Test Category',
            description='Test Description',
            department='Test Department',
            icon='fa-test'
        )
        
        db.session.add_all([admin, category])
        db.session.commit()
        
        # Add a complaint
        complaint = Complaint(
            title='Test Complaint',
            description='Test Description',
            location='Test Location',
            latitude=10.0,
            longitude=10.0,
            category_id=category.id,
            user_id=admin.id,
            status='pending',
            priority='medium'
        )
        
        db.session.add(complaint)
        db.session.commit()
    
    def tearDown(self):
        """Clean up test environment"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_app_exists(self):
        """Test that the app exists"""
        self.assertFalse(current_app is None)
    
    def test_app_is_testing(self):
        """Test that the app is in testing mode"""
        self.assertTrue(current_app.config['TESTING'])
    
    def test_app_is_using_sqlite(self):
        """Test that the app is using SQLite"""
        self.assertFalse(current_app.config['USE_FIREBASE'])
        self.assertTrue('sqlite' in current_app.config['SQLALCHEMY_DATABASE_URI'])
    
    def test_user_model(self):
        """Test that the User model works"""
        user = User.query.filter_by(username='admin_test').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'admin_test@example.com')
        self.assertEqual(user.role, 'admin')
        self.assertTrue(user.verify_password('Admin@123'))
    
    def test_category_model(self):
        """Test that the Category model works"""
        category = Category.query.filter_by(name='Test Category').first()
        self.assertIsNotNone(category)
        self.assertEqual(category.department, 'Test Department')
    
    def test_complaint_model(self):
        """Test that the Complaint model works"""
        complaint = Complaint.query.filter_by(title='Test Complaint').first()
        self.assertIsNotNone(complaint)
        self.assertEqual(complaint.status, 'pending')
        self.assertEqual(complaint.priority, 'medium')
        
        # Test relationships
        self.assertEqual(complaint.author.username, 'admin_test')
        self.assertEqual(complaint.category.name, 'Test Category')
    
    def test_crud_operations(self):
        """Test CRUD operations on the models"""
        # Create
        user = User(
            username='test_user',
            email='test@example.com',
            password='Test@123',
            first_name='Test',
            last_name='User',
            role='citizen'
        )
        db.session.add(user)
        db.session.commit()
        
        # Read
        retrieved_user = User.query.filter_by(username='test_user').first()
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.email, 'test@example.com')
        
        # Update
        retrieved_user.phone = '1234567890'
        db.session.commit()
        updated_user = User.query.filter_by(username='test_user').first()
        self.assertEqual(updated_user.phone, '1234567890')
        
        # Delete
        db.session.delete(retrieved_user)
        db.session.commit()
        deleted_user = User.query.filter_by(username='test_user').first()
        self.assertIsNone(deleted_user)

if __name__ == '__main__':
    unittest.main() 