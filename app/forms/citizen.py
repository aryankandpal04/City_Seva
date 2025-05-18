from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, SubmitField, FloatField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

class ComplaintForm(FlaskForm):
    title = StringField('Title', validators=[
        DataRequired(),
        Length(min=5, max=200, message='Title must be between 5 and 200 characters')
    ])
    
    description = TextAreaField('Description', validators=[
        DataRequired(),
        Length(min=10, max=1000, message='Description must be between 10 and 1000 characters')
    ])
    
    category = SelectField('Category', validators=[DataRequired()])
    
    location = StringField('Location', validators=[
        DataRequired(),
        Length(max=200, message='Location must be less than 200 characters')
    ])
    
    latitude = FloatField('Latitude', validators=[
        Optional(),
        NumberRange(min=-90, max=90, message='Invalid latitude value')
    ])
    
    longitude = FloatField('Longitude', validators=[
        Optional(),
        NumberRange(min=-180, max=180, message='Invalid longitude value')
    ])
    
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], validators=[DataRequired()])
    
    media_files = FileField('Media Files', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'mp4', 'mov'], 'Only image and video files are allowed!')
    ])
    
    submit = SubmitField('Submit Complaint')

class FeedbackForm(FlaskForm):
    rating = SelectField('Rating', choices=[
        ('1', '1 - Poor'),
        ('2', '2 - Fair'),
        ('3', '3 - Good'),
        ('4', '4 - Very Good'),
        ('5', '5 - Excellent')
    ], validators=[DataRequired()])
    
    comment = TextAreaField('Comment', validators=[
        Optional(),
        Length(max=500, message='Comment must be less than 500 characters')
    ])
    
    submit = SubmitField('Submit Feedback')

class ProfileUpdateForm(FlaskForm):
    first_name = StringField('First Name', validators=[
        DataRequired(),
        Length(min=2, max=50, message='First name must be between 2 and 50 characters')
    ])
    
    last_name = StringField('Last Name', validators=[
        DataRequired(),
        Length(min=2, max=50, message='Last name must be between 2 and 50 characters')
    ])
    
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=64, message='Username must be between 3 and 64 characters')
    ])
    
    email = StringField('Email', validators=[
        DataRequired(),
        Length(max=120, message='Email must be less than 120 characters')
    ])
    
    phone = StringField('Phone Number', validators=[
        Optional(),
        Length(max=20, message='Phone number must be less than 20 characters')
    ])
    
    address = TextAreaField('Address', validators=[
        Optional(),
        Length(max=200, message='Address must be less than 200 characters')
    ])
    
    profile_picture = FileField('Profile Picture', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Only image files are allowed!')
    ])
    
    submit = SubmitField('Update Profile') 