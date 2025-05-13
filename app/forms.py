from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, MultipleFileField
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms import SelectField, HiddenField, IntegerField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, Regexp
from app.models import User
from app.utils.constants import DEPARTMENTS, DEPARTMENTS_WITH_EMPTY, COMPLAINT_STATUSES, COMPLAINT_PRIORITIES
import re

class LoginForm(FlaskForm):
    """Form for user login"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    """Form for user registration"""
    first_name = StringField('First Name', validators=[DataRequired(), Length(1, 64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(1, 64)])
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(1, 64),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0, 'Usernames must start with a letter and can only contain letters, numbers, dots or underscores')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[
        Optional(), 
        Length(10, 20),
        Regexp('^\d+$', message='Phone number must contain only digits')
    ])
    address = TextAreaField('Address', validators=[Optional(), Length(5, 256)])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long'),
        Regexp('^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', 
               message='Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password')
    ])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

class ResetPasswordRequestForm(FlaskForm):
    """Form for requesting password reset"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    """Form for resetting password"""
    password = PasswordField('New Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long'),
        Regexp('^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', 
               message='Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password')
    ])
    submit = SubmitField('Reset Password')

class ProfileUpdateForm(FlaskForm):
    """Form for updating user profile"""
    first_name = StringField('First Name', validators=[DataRequired(), Length(1, 64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(1, 64)])
    phone = StringField('Phone Number', validators=[Optional(), Length(10, 20)])
    address = TextAreaField('Address', validators=[Optional(), Length(5, 256)])
    submit = SubmitField('Update Profile')

class ComplaintForm(FlaskForm):
    """Form for submitting complaints"""
    title = StringField('Title', validators=[DataRequired(), Length(5, 128)])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired(), Length(10, 1000)])
    location = StringField('Location', validators=[DataRequired(), Length(5, 256)])
    latitude = HiddenField('Latitude', validators=[DataRequired()])
    longitude = HiddenField('Longitude', validators=[DataRequired()])
    priority = SelectField('Priority', choices=COMPLAINT_PRIORITIES, default='medium')
    media_files = MultipleFileField('Attach Images or Videos (Multiple)', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi'], 'Images and videos only!')
    ])
    submit = SubmitField('Submit Complaint')

class ComplaintUpdateForm(FlaskForm):
    """Form for updating complaints"""
    status = SelectField('Status', choices=COMPLAINT_STATUSES)
    assigned_to_id = SelectField('Assign To', coerce=int, validators=[Optional()])
    comment = TextAreaField('Comment', validators=[DataRequired(), Length(5, 500)])
    submit = SubmitField('Update Complaint')

class FeedbackForm(FlaskForm):
    """Form for providing feedback on resolved complaints"""
    rating = SelectField('Rating', choices=[
        (5, '⭐⭐⭐⭐⭐ Excellent'),
        (4, '⭐⭐⭐⭐ Good'),
        (3, '⭐⭐⭐ Average'),
        (2, '⭐⭐ Below Average'),
        (1, '⭐ Poor')
    ], coerce=int, validators=[DataRequired()])
    comment = TextAreaField('Comment', validators=[Optional(), Length(5, 500)])
    submit = SubmitField('Submit Feedback')

class SearchForm(FlaskForm):
    """Form for searching complaints"""
    search_query = StringField('Search', validators=[Optional(), Length(2, 100)])
    category = SelectField('Category', coerce=int, validators=[Optional()])
    status = SelectField('Status', choices=[('', 'All')] + COMPLAINT_STATUSES, validators=[Optional()])
    priority = SelectField('Priority', choices=[('', 'All')] + COMPLAINT_PRIORITIES, validators=[Optional()])
    submit = SubmitField('Search')

class OfficialRequestForm(FlaskForm):
    """Form for requesting a government official account"""
    department = SelectField('Department', choices=DEPARTMENTS, validators=[DataRequired()])
    position = StringField('Official Position', validators=[DataRequired(), Length(3, 100)])
    employee_id = StringField('Employee ID', validators=[DataRequired(), Length(3, 50)])
    office_phone = StringField('Office Phone', validators=[DataRequired(), Length(10, 20)])
    justification = TextAreaField('Justification', validators=[DataRequired(), Length(20, 500)])
    terms = BooleanField('I confirm that all information provided is accurate and I am authorized to request an official account.', validators=[DataRequired()])
    submit = SubmitField('Submit Request')

class EnhancedRegistrationForm(RegistrationForm):
    """Enhanced registration form with role selection and official details"""
    role = SelectField('Register as', choices=[
        ('citizen', 'Citizen'), 
        ('official', 'Government Official')
    ], default='citizen', validators=[DataRequired()])
    
    # Official account fields (only required if role is 'official')
    department = SelectField('Department', choices=DEPARTMENTS, validators=[Optional()])
    position = StringField('Official Position', validators=[Optional(), Length(3, 100)])
    employee_id = StringField('Employee ID', validators=[Optional(), Length(3, 50)])
    office_phone = StringField('Office Phone', validators=[Optional(), Length(10, 20)])
    justification = TextAreaField('Why do you need an official account?', validators=[Optional(), Length(20, 500)])
    terms = BooleanField('I confirm that all information provided is accurate and I am authorized to request an official account.', validators=[Optional()])
    
    def validate(self, extra_validators=None):
        """Custom validation for official account fields"""
        initial_validation = super().validate(extra_validators=extra_validators)
        if not initial_validation:
            return False
            
        if self.role.data == 'official':
            if not self.department.data:
                self.department.errors = ['Department is required for officials']
                return False
            if not self.position.data:
                self.position.errors = ['Position is required for officials']
                return False
            if not self.employee_id.data:
                self.employee_id.errors = ['Employee ID is required for officials']
                return False
            if not self.office_phone.data:
                self.office_phone.errors = ['Office phone is required for officials']
                return False
            if not self.justification.data:
                self.justification.errors = ['Justification is required for officials']
                return False
            if not self.terms.data:
                self.terms.errors = ['You must confirm this statement']
                return False
                
        return True 

class EnhancedLoginForm(LoginForm):
    """Enhanced login form with department selection for officials"""
    role = SelectField('Login as', choices=[
        ('citizen', 'Citizen'),
        ('official', 'Government Official')
    ], default='citizen', validators=[DataRequired()])
    
    department = SelectField('Department', choices=DEPARTMENTS_WITH_EMPTY, validators=[Optional()])
    
    def validate(self, extra_validators=None):
        """Custom validation to require department for officials"""
        initial_validation = super().validate(extra_validators=extra_validators)
        if not initial_validation:
            return False
            
        if self.role.data == 'official' and not self.department.data:
            self.department.errors = ['Department is required for Government Officials']
            return False
                
        return True 