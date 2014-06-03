# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0015_userlecturepageanswer'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL, to_field='id')),
                ('student_id', models.IntegerField(verbose_name='Student number', blank=True, null=True)),
                ('study_program', models.CharField(verbose_name='Study program', blank=True, max_length=80, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
