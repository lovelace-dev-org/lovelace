#!/usr/bin/env python
"""
Create an example file upload exercise for easy testing.
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lovelace.settings")

import django
django.setup()

from courses.models import FileUploadExercise

new_exercise = FileUploadExercise.objects.create()
