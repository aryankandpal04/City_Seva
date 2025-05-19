# CitySeva Web Application

CitySeva is a civic complaint management system that allows citizens to report issues to their local government. Officials can track, manage, and resolve these complaints, creating a transparent and efficient system for civic governance.

## Features

- User accounts with different roles (citizen, official, admin)
- Complaint submission with categories, location, and image uploads
- Real-time tracking of complaint status
- Official account requests and approval workflow
- Notifications for status updates
- Dashboard with statistics and reports
- Mobile-responsive design

## Database System

CitySeva uses SQLite as its exclusive database system:
- Simple, lightweight, and fast
- Zero configuration required
- File-based database stored locally
- No external services or dependencies needed
- Perfect for local deployment and testing

## Setup Instructions

### Prerequisites

- Python 3.8+
- Pip (Python package manager)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/CitySeva_WebApp.git
   cd CitySeva_WebApp
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```
   # On Windows:
   run.bat
   
   # On Mac/Linux:
   chmod +x run.sh
   ./run.sh
   ```

### Running the Application

1. Start the development server:
   ```
   flask run
   ```

2. Access the application at http://localhost:5000

## Database Schema

The application uses SQLAlchemy ORM with the following models:

- `User`: User accounts with different roles (citizen, official, admin)
- `Category`: Categories for complaints
- `Complaint`: The main complaint records
- `ComplaintUpdate`: Updates/comments on complaints
- `Feedback`: User feedback on resolved complaints
- `Notification`: User notifications
- `ComplaintMedia`: Media attachments for complaints

For more details on the database schema, see the `app/models.py` file.

## License

[MIT License](LICENSE)

## Contributors

- [Aryan Kandpal](https://www.linkedin.com/in/aryan-kandpal-a7227424b/)

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript, Bootstrap, jQuery, Chart.js, Leaflet.js, SweetAlert2
- **Backend**: Flask (Python), Flask-Login, Flask-WTF, Flask-Mail, Jinja2, Flask-SQLAlchemy
- **Database**: SQLite

## Sample Users

The sample data includes the following users that you can use to test the application:

- **Admin User**:
  - Email: admin@cityseva.com
  - Password: Admin@123

- **Water Department Official**:
  - Email: water@cityseva.com
  - Password: Water@123

- **Public Works Official**:
  - Email: road@cityseva.com
  - Password: Road@123

- **Citizen 1**:
  - Email: john@example.com
  - Password: John@123

- **Citizen 2**:
  - Email: jane@example.com
  - Password: Jane@123

## Project Structure

```
CitySeva_WebApp/
├── app/                                # Main application package
│   ├── __init__.py                     # Application factory, extensions initialization
│   ├── forms/                          # Form definitions (modular approach)
│   │   ├── __init__.py                 # Package initialization
│   │   ├── admin.py                    # Admin-specific forms (category management, etc.)
│   │   ├── auth.py                     # Authentication forms (login, register, reset password)
│   │   ├── citizen.py                  # Citizen-specific forms (complaint submission, feedback)
│   │   └── contact.py                  # Contact form for the contact page
│   ├── forms.py                        # Legacy form definitions (being migrated to forms/)
│   ├── models.py                       # SQLAlchemy ORM models for database tables
│   │   ├── User                        # User model for citizens, officials, admins
│   │   ├── Category                    # Complaint categories
│   │   ├── Complaint                   # Citizen complaints/issues
│   │   ├── ComplaintUpdate             # Status updates and comments on complaints
│   │   ├── Feedback                    # User feedback on resolved complaints
│   │   ├── AuditLog                    # System event logging
│   │   ├── Notification                # User notifications
│   │   ├── OfficialRequest             # Requests for official accounts
│   │   └── ComplaintMedia              # Media attachments for complaints
│   ├── routes/                         # Route definitions (URL handlers)
│   │   ├── admin.py                    # Admin dashboard routes (1150+ lines)
│   │   ├── api.py                      # API endpoints for internal use
│   │   ├── api_v1.py                   # Public REST API endpoints
│   │   ├── auth.py                     # Authentication routes (login, register, password reset)
│   │   ├── citizen.py                  # Citizen-specific routes (complaints, feedback)
│   │   ├── government_officials.py     # Routes for government officials
│   │   └── main.py                     # Main routes (home, about, contact)
│   ├── static/                         # Static assets
│   │   ├── css/
│   │   │   └── styles.css              # Main CSS styles (1000+ lines)
│   │   ├── img/                        # Static images
│   │   ├── js/
│   │   │   ├── scripts.js              # Main JavaScript functionality
│   │   │   └── service-worker.js       # PWA service worker implementation
│   │   ├── uploads/                    # User-uploaded media (complaint photos)
│   │   ├── manifest.json               # PWA manifest file
│   │   └── offline.html                # Offline page for PWA
│   ├── templates/                      # Jinja2 HTML templates
│   │   ├── admin/                      # Admin interface templates
│   │   │   ├── add_category.html       # Category creation
│   │   │   ├── categories.html         # Category management
│   │   │   ├── complaint_detail.html   # Detailed complaint view for admins
│   │   │   ├── complaints.html         # All complaints management
│   │   │   ├── dashboard.html          # Admin dashboard
│   │   │   ├── official_requests.html  # Manage official account requests
│   │   │   ├── reports.html            # Analytics and reports
│   │   │   ├── request_detail.html     # Official request details
│   │   │   ├── send_notification.html  # Send notifications to users
│   │   │   └── users.html              # User management
│   │   ├── auth/                       # Authentication templates
│   │   │   ├── login.html              # User login
│   │   │   ├── register.html           # User registration
│   │   │   ├── request_official_account.html # Request official account
│   │   │   ├── reset_password.html     # Reset password form
│   │   │   ├── reset_password_otp.html # Reset password with OTP
│   │   │   └── verify_otp.html         # Email verification with OTP
│   │   ├── citizen/                    # Citizen interface templates
│   │   │   ├── complaint_detail.html   # Detailed complaint view
│   │   │   ├── complaints.html         # User's complaints listing
│   │   │   ├── dashboard.html          # Citizen dashboard
│   │   │   ├── new_complaint.html      # New complaint submission form
│   │   │   ├── profile.html            # User profile
│   │   │   └── provide_feedback.html   # Feedback form for resolved complaints
│   │   ├── email/                      # Email templates for notifications
│   │   ├── errors/                     # Error pages (404, 500, etc.)
│   │   ├── government_officials/       # Official interface templates
│   │   │   ├── assigned_complaints.html # Complaints assigned to official
│   │   │   ├── complaint_detail.html   # Detailed complaint view for officials
│   │   │   ├── dashboard.html          # Official dashboard with analytics
│   │   │   ├── profile.html            # Official profile management
│   │   │   └── reports.html            # Department-specific reports
│   │   ├── shared/                     # Shared template components
│   │   ├── about.html                  # About page
│   │   ├── api_docs.html               # API documentation page
│   │   ├── base.html                   # Base template with common layout
│   │   ├── contact.html                # Contact page
│   │   └── index.html                  # Homepage
│   └── utils/                          # Utility functions and helpers
│       ├── constants.py                # Application constants
│       ├── context_processors.py       # Template context processors
│       ├── decorators.py               # Custom route decorators
│       ├── email.py                    # Email sending functionality
│       ├── fallback_email.py           # Fallback email implementation
│       ├── notifications.py            # Notification generation and delivery
│       ├── otp.py                      # OTP generation and verification
│       └── smtp_patch.py               # SMTP compatibility patches
├── instance/                           # Instance-specific configurations
├── migrations/                         # Database migration files (Flask-Migrate)
├── .gitignore                          # Git ignore file
├── DEVELOPMENT_STATUS.md               # Current development status and roadmap
├── GOOGLE_MAPS_API_SETUP.md            # Guide for setting up Google Maps API
├── README.md                           # Project documentation
├── app.yaml                            # Google Cloud App Engine configuration
├── cityseva.env                        # Environment variables template
├── config.py                           # Application configuration
│   ├── Config                          # Base configuration class
│   ├── DevelopmentConfig               # Development environment config
│   ├── TestingConfig                   # Testing environment config
│   └── ProductionConfig                # Production environment config
├── init_db.py                          # Database initialization script
├── requirements.txt                    # Python dependencies
│   ├── Flask==2.3.3                    # Web framework
│   ├── Flask-Login==0.6.3              # User authentication
│   ├── Flask-SQLAlchemy==3.1.1         # ORM for database
│   ├── Flask-WTF==1.2.1                # Form handling
│   ├── Flask-Mailman==0.3.0            # Email functionality
│   └── (other dependencies)            # Additional libraries
├── run.bat                             # Windows startup script
├── run.py                              # Application entry point
├── run.sh                              # Unix startup script
├── test_email.py                       # Email testing script
└── update_db.py                        # Database update/migration script
```

## Key Components

### Database Models

The application uses SQLAlchemy ORM with the following models:

- **User**: Multi-role user accounts (citizen, official, admin) with authentication support
- **Category**: Categories for complaints with department assignments
- **Complaint**: Core complaint records with location, status tracking, and assignment
- **ComplaintUpdate**: History of status changes and comments on complaints
- **Feedback**: User ratings and feedback on resolved complaints
- **AuditLog**: System event logging for security and auditing
- **Notification**: User notification system
- **OfficialRequest**: Requests and approval workflow for official accounts
- **ComplaintMedia**: Media attachments for complaints

### Configuration System

The application uses a flexible configuration system with different environments:

- **Development**: Local development with debugging
- **Testing**: Configuration for automated tests
- **Production**: Optimized for deployment with security features

Configuration can be customized through environment variables or the `cityseva.env` file.

### Authentication System

- Secure password hashing with Werkzeug
- OTP-based email verification
- Password reset functionality
- Role-based access control
- Account lockout protection against brute force attacks

### Complaint Workflow

1. Citizens submit complaints with location, category, and optional media
2. Admins review and assign complaints to appropriate officials
3. Officials update status and add progress comments
4. When resolved, citizens can provide feedback and ratings
5. Notifications are sent at each stage of the process

### User Interfaces

- **Citizen Portal**: Submit and track complaints, provide feedback
- **Official Dashboard**: Manage assigned complaints, view performance metrics
- **Admin Console**: User management, complaint oversight, and system configuration

## Development

To contribute to this project:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to your branch: `git push origin feature-name`
5. Submit a pull request
