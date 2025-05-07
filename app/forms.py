from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms import SelectField, HiddenField, IntegerField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from app.models import User

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
    username = StringField('Username', validators=[DataRequired(), Length(1, 64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[Optional(), Length(10, 20)])
    address = TextAreaField('Address', validators=[Optional(), Length(5, 256)])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long')
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
        Length(min=8, message='Password must be at least 8 characters long')
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
    latitude = HiddenField('Latitude', validators=[Optional()])
    longitude = HiddenField('Longitude', validators=[Optional()])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'), 
        ('medium', 'Medium'), 
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='medium')
    image = FileField('Attach Image', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    submit = SubmitField('Submit Complaint')

class ComplaintUpdateForm(FlaskForm):
    """Form for updating complaints"""
    status = SelectField('Status', choices=[
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'), 
        ('resolved', 'Resolved'), 
        ('rejected', 'Rejected')
    ])
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
    status = SelectField('Status', choices=[
        ('', 'All'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'), 
        ('resolved', 'Resolved'), 
        ('rejected', 'Rejected')
    ], validators=[Optional()])
    priority = SelectField('Priority', choices=[
        ('', 'All'),
        ('low', 'Low'), 
        ('medium', 'Medium'), 
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], validators=[Optional()])
    submit = SubmitField('Search') 