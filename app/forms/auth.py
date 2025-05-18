from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional, Regexp
from app.models import User
from app.utils.constants import DEPARTMENTS, DEPARTMENTS_WITH_EMPTY

class EnhancedLoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    role = SelectField('Login as', choices=[
        ('citizen', 'Citizen'),
        ('official', 'Government Official')
    ], default='citizen', validators=[DataRequired()])
    department = SelectField('Department', choices=DEPARTMENTS_WITH_EMPTY, validators=[Optional()])
    submit = SubmitField('Sign In')
    
    def validate(self, extra_validators=None):
        """Custom validation to require department for officials"""
        initial_validation = super().validate(extra_validators=extra_validators)
        if not initial_validation:
            return False
            
        if self.role.data == 'official' and not self.department.data:
            self.department.errors = ['Department is required for Government Officials']
            return False
                
        return True

class EnhancedRegistrationForm(FlaskForm):
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
        Length(min=3, max=64, message='Username must be between 3 and 64 characters'),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0, 'Usernames must start with a letter and can only contain letters, numbers, dots or underscores')
    ])
    
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120, message='Email must be less than 120 characters')
    ])
    
    phone = StringField('Phone Number', validators=[
        Optional(),
        Length(max=20, message='Phone number must be less than 20 characters'),
        Regexp(r'^\d+$', message='Phone number must contain only digits')
    ])
    
    address = TextAreaField('Address', validators=[
        Optional(),
        Length(max=200, message='Address must be less than 200 characters')
    ])
    
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long'),
        Regexp(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$',
               message='Password must contain at least one letter, one number, and one special character')
    ])
    
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    
    role = SelectField('Role', choices=[
        ('citizen', 'Citizen'),
        ('official', 'Government Official')
    ])
    
    # Official account fields
    department = SelectField('Department', choices=DEPARTMENTS, validators=[Optional()])
    position = StringField('Official Position', validators=[Optional(), Length(3, 100)])
    employee_id = StringField('Employee ID', validators=[Optional(), Length(3, 50)])
    office_phone = StringField('Office Phone', validators=[Optional(), Length(10, 20)])
    justification = TextAreaField('Why do you need an official account?', validators=[Optional(), Length(20, 500)])
    terms = BooleanField('I confirm that all information provided is accurate and I am authorized to request an official account.', validators=[Optional()])
    
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')
            
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

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address')
    ])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')

class ResetPasswordOTPForm(FlaskForm):
    otp = StringField('OTP', validators=[
        DataRequired(),
        Length(min=6, max=6, message='OTP must be 6 digits')
    ])
    submit = SubmitField('Verify OTP') 