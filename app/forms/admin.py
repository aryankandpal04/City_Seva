from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Optional

class ComplaintUpdateForm(FlaskForm):
    status = SelectField('Status', choices=[
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected')
    ], validators=[DataRequired()])
    
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], validators=[DataRequired()])
    
    assigned_to = SelectField('Assign To', coerce=int, validators=[Optional()])
    
    comment = TextAreaField('Comment', validators=[
        DataRequired(),
        Length(max=500, message='Comment must be less than 500 characters')
    ])
    
    complaint_id = HiddenField('Complaint ID')
    
    submit = SubmitField('Update Complaint')
    
    def __init__(self, *args, **kwargs):
        super(ComplaintUpdateForm, self).__init__(*args, **kwargs)
        # Set default choices for status and priority
        self.status.choices = [
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('resolved', 'Resolved'),
            ('rejected', 'Rejected')
        ]
        self.priority.choices = [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent')
        ]

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[
        Optional(),
        Length(max=100, message='Search query must be less than 100 characters')
    ])
    
    category = SelectField('Category', validators=[Optional()])
    
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
    
    date_from = StringField('From Date', validators=[Optional()])
    date_to = StringField('To Date', validators=[Optional()])
    
    submit = SubmitField('Search') 