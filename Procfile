release: python manage.py migrate --noinput && python manage.py seed_store
web: gunicorn egrocery.wsgi --log-file -
