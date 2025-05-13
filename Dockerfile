FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Make sure database directory exists
RUN mkdir -p instance

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Run database migrations and initialization
RUN python init_db.py

# Expose port
EXPOSE 8080

# Run the application with gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 run:app 