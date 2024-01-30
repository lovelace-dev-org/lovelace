# Generated by Django 4.1 on 2024-01-22 12:43

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AssessmentBullet",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("point_value", models.FloatField()),
                ("ordinal_number", models.PositiveSmallIntegerField()),
                ("title", models.CharField(max_length=255)),
                ("title_en", models.CharField(max_length=255, null=True)),
                ("title_fi", models.CharField(max_length=255, null=True)),
                ("tooltip", models.TextField(blank=True, default="")),
                ("tooltip_en", models.TextField(blank=True, default="", null=True)),
                ("tooltip_fi", models.TextField(blank=True, default="", null=True)),
            ],
        ),
        migrations.CreateModel(
            name="AssessmentSection",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("title_en", models.CharField(max_length=255, null=True)),
                ("title_fi", models.CharField(max_length=255, null=True)),
                ("ordinal_number", models.PositiveSmallIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name="AssessmentSheet",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("title_en", models.CharField(max_length=255, null=True)),
                ("title_fi", models.CharField(max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="AssessmentToExerciseLink",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("revision", models.PositiveIntegerField(blank=True, null=True)),
            ],
        ),
    ]