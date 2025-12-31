#!/usr/bin/env bash
# Exit on error
set -o errexit

# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate

# Create logs directory if it doesn't exist
mkdir -p logs