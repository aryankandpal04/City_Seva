#!/bin/bash
echo "CitySeva Application Setup"

echo "Checking for existing database..."
if [ -f "instance/cityseva.db" ]; then
    echo "Existing database found."
    read -p "Do you want to recreate the database with sample data? (y/n): " choice
    if [ "$choice" != "y" ] && [ "$choice" != "Y" ]; then
        echo "Using existing database."
    else
        echo "Initializing database with sample data..."
        python3 init_db.py
        if [ $? -ne 0 ]; then
            echo "Failed to initialize database."
            exit 1
        fi
    fi
else
    echo "No existing database found. Will create a new one."
    echo "Initializing database with sample data..."
    python3 init_db.py
    if [ $? -ne 0 ]; then
        echo "Failed to initialize database."
        exit 1
    fi
fi

echo "Starting CitySeva application..."
export FLASK_APP=run.py
export FLASK_ENV=development
export FLASK_DEBUG=1
flask run

echo "Application stopped." 