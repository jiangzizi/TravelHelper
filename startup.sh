#!/bin/bash
# python manage.py collectstatic --noinput
source ~/.bashrc
yum install -y nodejs
echo $PATH
npx -v
pwd
gunicorn --workers 2 --bind 0.0.0.0:8080 TravelHelper.wsgi --timeout 300
