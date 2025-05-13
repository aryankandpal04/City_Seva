@echo off
echo CitySeva Application Setup

echo Checking for existing database...
if exist instance\cityseva.db (
    echo Existing database found.
    choice /C YN /M "Do you want to recreate the database with sample data"
    if errorlevel 2 goto run_app
) else (
    echo No existing database found. Will create a new one.
)

echo Initializing database with sample data...
python init_db.py
if errorlevel 1 (
    echo Failed to initialize database.
    pause
    exit /b 1
)

:run_app
echo Starting CitySeva application...
set FLASK_APP=run.py
set FLASK_ENV=development
set FLASK_DEBUG=1
flask run
pause 