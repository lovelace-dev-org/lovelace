#!/bin/bash

# Source for faketty: http://stackoverflow.com/a/20401674
function faketty { script -qfc "$(printf "%q " "$@")"; }

ADMIN_USERNAME="admin"
ADMIN_EMAIL=""
ADMIN_PASSWD="admin"

# Destroy the old stuff
sudo -u postgres dropdb lovelace
rm -rf courses/migrations/00* courses/migrations/__pycache__/ feedback/migrations/00* feedback/migrations/__pycache__/
rm -rf upload/

# Create the new stuff
sudo -u postgres createdb --owner=lovelace lovelace
mkdir upload
python manage.py makemigrations
python manage.py migrate
#echo -e "$ADMIN_USERNAME\n$ADMIN_EMAIL\n$ADMIN_PASSWD\n$ADMIN_PASSWD\n\n" | faketty python manage.py createsuperuser
#echo -e "$ADMIN_USERNAME\n$ADMIN_EMAIL" ; echo -e "$ADMIN_PASSWD\n$ADMIN_PASSWD" >&2 | faketty python manage.py createsuperuser
python create_file_exercise.py Example

