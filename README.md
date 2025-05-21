# CitySeva Web Application

CitySeva is a comprehensive civic complaint management system that facilitates seamless communication between citizens and local government officials. The platform enables citizens to report issues, track their resolution status, and provide feedback, while officials can efficiently manage and resolve complaints within their departments.

## Key Features

### For Citizens
- User-friendly complaint submission with location mapping
- Real-time complaint status tracking
- Image upload support for complaint documentation
- Feedback system for resolved complaints
- Email notifications for status updates
- Mobile-responsive interface

### For Government Officials
- Department-specific dashboard
- Complaint assignment and management
- Status updates and resolution tracking
- Analytics and reporting tools
- Bulk notification system
- Department performance metrics

### For Administrators
- User management (citizens and officials)
- Department and category management
- Official account approval workflow
- System-wide analytics and reports
- Audit logging and security monitoring
- Email template management

## Technical Stack

### Frontend
- HTML5, CSS3, JavaScript (ES6+)
- Bootstrap 5.3.0 for responsive design
- jQuery 3.7.1 for DOM manipulation
- Chart.js for data visualization
- SweetAlert2 for enhanced alerts
- Select2 for advanced select inputs
- AOS (Animate On Scroll) for animations

### Backend
- Flask 2.3.3 (Python web framework)
- SQLAlchemy 2.0.27 (ORM)
- Flask-Login 0.6.3 (Authentication)
- Flask-WTF 1.2.1 (Form handling)
- Flask-Mailman 0.3.0 (Email functionality)
- Flask-JWT-Extended 4.5.3 (API authentication)

### Database
- SQLite (Primary database)
- Alembic 1.13.1 (Database migrations)

### Security Features
- Password hashing with bcrypt
- JWT-based API authentication
- Rate limiting for login attempts
- OTP-based email verification
- Session management
- CSRF protection
- XSS prevention

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git

### Setup Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/CitySeva_WebApp.git
   cd CitySeva_WebApp
   ```

2. Create and activate virtual environment:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   # Copy the template
   cp cityseva.env.example cityseva.env
   # Edit cityseva.env with your configuration
   ```

5. Initialize the database:
   ```bash
   # Windows
   run.bat

   # Linux/Mac
   chmod +x run.sh
   ./run.sh
   ```

6. Start the development server:
   ```bash
   flask run
   ```

## Configuration

The application can be configured through environment variables in `cityseva.env`:

- `FLASK_APP`: Application entry point
- `FLASK_ENV`: Development/Production mode
- `SECRET_KEY`: Application secret key
- `MAIL_SERVER`: SMTP server settings
- `MAIL_PORT`: SMTP port
- `MAIL_USERNAME`: SMTP username
- `MAIL_PASSWORD`: SMTP password
- `GOOGLE_MAPS_API_KEY`: Google Maps API key

## Development

### Code Style
- Follow PEP 8 guidelines
- Use Black for code formatting
- Use isort for import sorting
- Use flake8 for linting

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/
```

### Database Migrations
```bash
# Create a new migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade
```

## Deployment

### Production Setup
1. Set up a production-grade WSGI server (Gunicorn)
2. Configure a reverse proxy (Nginx/Apache)
3. Set up SSL certificates
4. Configure production environment variables
5. Set up database backups

### Docker Deployment
```bash
# Build the image
docker build -t cityseva .

# Run the container
docker run -p 5000:5000 cityseva
```

## API Documentation

The application provides a RESTful API for integration with other systems. API documentation is available at `/api/docs` when running the application.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please:
1. Check the [documentation](docs/)
2. Open an issue on GitHub
3. Contact the development team

## Acknowledgments

- [Aryan Kandpal](https://www.linkedin.com/in/aryan-kandpal-a7227424b/) - Lead Developer
- All contributors and supporters of the project
