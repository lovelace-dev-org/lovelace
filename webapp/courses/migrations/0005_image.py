# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
import courses.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0004_file_filetaskreturnfile'),
    ]

    operations = [
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('uploader', models.ForeignKey(to=settings.AUTH_USER_MODEL, to_field='id')),
                ('name', models.CharField(unique=True, max_length=200, verbose_name='Name for reference in content')),
                ('date_uploaded', models.DateTimeField(verbose_name='date uploaded')),
                ('description', models.CharField(max_length=500)),
                ('fileinfo', models.ImageField(upload_to=courses.models.get_image_upload_path)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
