#!/usr/bin/env bash
# Build script used by Render (and handy on any Linux server).
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py seed_store

# Create the admin account on first deploy if these variables are set
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python manage.py createsuperuser --noinput || true
fi
