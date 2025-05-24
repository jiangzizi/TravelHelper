#!/bin/bash
# python manage.py collectstatic --noinput
python3 -m gunicorn --workers 2 --bind 0.0.0.0:8080 TravelHelper.wsgi --timeout 300
