#!/bin/bash
set -eEu -o pipefail
python manage.py makemigrations
python manage.py migrate 
python manage.py makemigrations emiss_parse
python manage.py migrate  emiss_parse
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(is_superuser=True).exists() or User.objects.create_superuser('administrator', 'admin@admin.com', '${DJANGO_ADMINISTRATOR_PASS}');"
exec python manage.py runserver  0.0.0.0:8000