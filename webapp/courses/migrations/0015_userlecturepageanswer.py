# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
import courses.models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0014_userfiletaskanswer'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserLecturePageAnswer',
            fields=[
                ('useranswer_ptr', models.OneToOneField(auto_created=True, serialize=False, to='courses.UserAnswer', primary_key=True, to_field='id')),
                ('task', models.ForeignKey(to='courses.LecturePage', to_field='contentpage_ptr')),
                ('answered', models.BooleanField(verbose_name=courses.models.LecturePage, default=None)),
            ],
            options={
            },
            bases=('courses.useranswer',),
        ),
    ]
