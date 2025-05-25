#!/bin/bash
# python manage.py collectstatic --noinput
source ~/.bashrc
echo $PATH
npx -v
gunicorn --workers 2 --bind 0.0.0.0:8080 TravelHelper.wsgi --timeout 300
