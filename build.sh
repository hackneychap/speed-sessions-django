#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

npm install
npm run build:css

python manage.py collectstatic --no-input

# One-off, idempotent repair: some databases applied allauth's socialaccount
# migrations before django.contrib.sites existed, which makes Django's
# migration consistency check fail. Applying the sites migrations with
# socialaccount removed from INSTALLED_APPS fixes the history. No-op once done.
python manage.py migrate sites --settings=speed_sessions.settings_repair --noinput

python manage.py migrate --noinput