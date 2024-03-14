# Generated by Django 4.1 on 2024-03-13 12:31

from django.db import migrations
from utils.management import get_prefixed_slug

def initialize_sheets(apps, schema_editor):
    AssessmentSheet = apps.get_model("assessment", "AssessmentSheet")
    for sheet in AssessmentSheet.objects.all():
        sheet.slug = get_prefixed_slug(sheet, sheet.origin, "title")
        assert sheet.slug is not None
        sheet.save()


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0007_guess_prefixes"),
        ("assessment", "0003_rename_course_assessmentsheet_origin_and_more"),
    ]

    operations = [
        migrations.RunPython(initialize_sheets)
    ]
