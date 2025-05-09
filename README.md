# CitySeva Web Application
 
A secure, transparent, and user-friendly web-based platform that enables residents to report civic issues, track the status of their complaints, and provide feedback on city services.
 
## Features
 
- User Registration & Authentication for citizens and government officials 
- Complaint submission with categories, images, and location data 
- Real-time tracking and status updates 
- Feedback and ratings system 
- Admin dashboard for complaint management 
- Analytics and reporting 
- Notification system 
- Mobile-responsive design 
 
## Tech Stack
 
- **Frontend**: HTML, CSS, JavaScript, Bootstrap, jQuery, Chart.js, Leaflet.js, SweetAlert2 
- **Backend**: Flask (Python), Flask-Login, Flask-WTF, Flask-Mail, Jinja2, Flask-SQLAlchemy 
- **Database**: SQLite 
 
## Installation 
 
1. Clone the repository: 
   ```
   git clone https://github.com/yourusername/CitySeva_WebApp.git
   cd CitySeva_WebApp
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the project root with the following variables (customize as needed):
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-for-development-only
   DATABASE_URL=sqlite:///cityseva.db
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   MAIL_DEFAULT_SENDER=no-reply@cityseva.com
   GOOGLE_MAPS_API_KEY=your-google-maps-api-key
   ```

6. Initialize the database with sample data:
   ```
   python init_db.py --reset
   ```

7. Run the application:
   ```
   python run.py
   ```

8. Open a web browser and navigate to `http://127.0.0.1:5000`

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
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   ├── img/
│   │   └── uploads/
│   ├── templates/
│   │   ├── admin/
│   │   ├── auth/
│   │   ├── citizen/
│   │   ├── email/
│   │   └── errors/
│   ├── models.py
│   ├── forms.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── citizen.py
│   │   ├── admin.py
│   │   └── api.py
│   ├── utils/
│   │   ├── email.py
│   │   ├── decorators.py
│   │   └── context_processors.py
│   └── __init__.py
├── config.py
├── requirements.txt
├── init_db.py
└── run.py
```

## Development

To contribute to this project:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to your branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. #   C i t y _ S e v a 
 
 
