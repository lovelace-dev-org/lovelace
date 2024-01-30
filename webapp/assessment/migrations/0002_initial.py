# Generated by Django 4.1 on 2024-01-22 12:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("assessment", "0001_initial"),
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessmenttoexerciselink",
            name="exercise",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="courses.contentpage"
            ),
        ),
        migrations.AddField(
            model_name="assessmenttoexerciselink",
            name="instance",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="courses.courseinstance"
            ),
        ),
        migrations.AddField(
            model_name="assessmenttoexerciselink",
            name="sheet",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="assessment.assessmentsheet",
            ),
        ),
        migrations.AddField(
            model_name="assessmentsheet",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="courses.course"
            ),
        ),
        migrations.AddField(
            model_name="assessmentsection",
            name="sheet",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="assessment.assessmentsheet",
            ),
        ),
        migrations.AddField(
            model_name="assessmentbullet",
            name="section",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="assessment.assessmentsection",
            ),
        ),
        migrations.AddField(
            model_name="assessmentbullet",
            name="sheet",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="assessment.assessmentsheet",
            ),
        ),
    ]