# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0012_filetasktestincludefile_radiobuttontask_textfieldtask'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserAnswer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('evaluation', models.OneToOneField(to='courses.Evaluation', to_field='id')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, to_field='id')),
                ('answer_date', models.DateTimeField(verbose_name='Date and time of when the user answered this task')),
                ('collaborators', models.TextField(verbose_name='Which users was this task answered with', blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
