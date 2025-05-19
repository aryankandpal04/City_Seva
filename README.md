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

- [Your Name](https://github.com/yourusername)

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
├── app/
│   ├── __init__.py
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── auth.py
│   │   ├── citizen.py
│   │   └── contact.py
│   ├── forms.py
│   ├── models.py
│   ├── routes/
│   │   ├── admin.py
│   │   ├── api.py
│   │   ├── api_v1.py
│   │   ├── auth.py
│   │   ├── citizen.py
│   │   ├── government_officials.py
│   │   └── main.py
│   ├── static/
│   │   ├── css/
│   │   ├── img/
│   │   ├── js/
│   │   ├── uploads/
│   │   ├── manifest.json
│   │   └── offline.html
│   ├── templates/
│   │   ├── admin/
│   │   ├── auth/
│   │   ├── citizen/
│   │   ├── email/
│   │   ├── errors/
│   │   ├── government_officials/
│   │   ├── shared/
│   │   ├── about.html
│   │   ├── api_docs.html
│   │   ├── base.html
│   │   ├── contact.html
│   │   └── index.html
│   └── utils/
│       ├── constants.py
│       ├── context_processors.py
│       ├── decorators.py
│       ├── email.py
│       ├── fallback_email.py
│       ├── notifications.py
│       ├── otp.py
│       └── smtp_patch.py
├── instance/
├── migrations/
├── .gitignore
├── DEVELOPMENT_STATUS.md
├── GOOGLE_MAPS_API_SETUP.md
├── README.md
├── app.yaml
├── cityseva.env
├── config.py
├── init_db.py
├── requirements.txt
├── run.bat
├── run.py
├── run.sh
├── test_email.py
└── update_db.py
```

## Development

To contribute to this project:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to your branch: `git push origin feature-name`
5. Submit a pull request
