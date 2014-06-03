# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
import courses.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0003_contentfeedbackuseranswer'),
    ]

    operations = [
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('uploader', models.ForeignKey(to=settings.AUTH_USER_MODEL, to_field='id')),
                ('name', models.CharField(unique=True, max_length=200, verbose_name='Name for reference in content')),
                ('date_uploaded', models.DateTimeField(verbose_name='date uploaded')),
                ('typeinfo', models.CharField(max_length=200)),
                ('fileinfo', models.FileField(upload_to=courses.models.get_file_upload_path)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FileTaskReturnFile',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('returnable', models.ForeignKey(to='courses.FileTaskReturnable', to_field='id')),
                ('fileinfo', models.FileField(upload_to=courses.models.get_answerfile_path)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
