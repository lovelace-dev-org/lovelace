# Generated by Django 4.1 on 2024-03-13 12:30

from django.db import migrations


def guess_prefixes(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    for course in Course.objects.all():
        slug_parts = course.slug.split("-")
        if len(slug_parts) > 1:
            prefix = "".join(part[0] for part in slug_parts)
        else:
            prefix = course.slug[:4]
        course.prefix = prefix
        course.save()



class Migration(migrations.Migration):
    dependencies = [
        (
            "courses",
            "0006_rename_course_term_origin_alter_term_unique_together_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(guess_prefixes)

    ]
