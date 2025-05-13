"""
Constants and configuration values used throughout the application
"""

# Department definitions - centralized here for easy maintenance
DEPARTMENTS = [
    ('Electricity Board', 'Electricity Board'),
    ('Sanitation', 'Sanitation'),
    ('Parks & Recreation', 'Parks & Recreation'),
    ('Transport', 'Transport'),
    ('Public Works', 'Public Works'),
    ('Animal Control', 'Animal Control'),
    ('Water Department', 'Water Department'),
    ('Other', 'Other')
]

# Same list but with empty option for forms that need it
DEPARTMENTS_WITH_EMPTY = [('', 'Select Department')] + DEPARTMENTS

# Statuses for complaints
COMPLAINT_STATUSES = [
    ('pending', 'Pending'),
    ('in_progress', 'In Progress'),
    ('resolved', 'Resolved'),
    ('rejected', 'Rejected')
]

# Priorities for complaints
COMPLAINT_PRIORITIES = [
    ('low', 'Low'), 
    ('medium', 'Medium'), 
    ('high', 'High'),
    ('urgent', 'Urgent')
] 