#!/bin/bash

# Security-focused startup script for TravelHelper

# Check for required environment variables
required_vars=("SECRET_KEY" "DB_PASSWORD" "SOA_KEY")
for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "ERROR: Required environment variable $var is not set"
        echo "Please check your .env file or environment configuration"
        exit 1
    fi
done

# Verify DEBUG is set to False in production
if [[ "$DEBUG" == "true" || "$DEBUG" == "True" ]]; then
    echo "WARNING: DEBUG is enabled. This should be False in production."
    if [[ "$ENVIRONMENT" == "production" ]]; then
        echo "ERROR: Cannot run in production with DEBUG=True"
        exit 1
    fi
fi

# Run database migrations (safely)
echo "Running database migrations..."
python manage.py migrate --check 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Running database migrations..."
    python manage.py migrate
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Security check
echo "Running security check..."
python manage.py check --deploy --fail-level WARNING

if [ $? -eq 0 ]; then
    echo "Starting TravelHelper server securely..."
    # Use more workers in production, limit request size
    gunicorn --workers 2 \
             --max-requests 1000 \
             --max-requests-jitter 50 \
             --timeout 30 \
             --keep-alive 5 \
             --limit-request-line 2048 \
             --limit-request-fields 50 \
             --limit-request-field_size 8190 \
             TravelHelper.wsgi
else
    echo "ERROR: Security check failed. Please review the warnings above."
    exit 1
fi