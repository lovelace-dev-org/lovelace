# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0008_checkboxtask'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileTask',
            fields=[
                ('taskpage_ptr', models.OneToOneField(to='courses.TaskPage', auto_created=True, primary_key=True, serialize=False, to_field='contentpage_ptr')),
            ],
            options={
            },
            bases=('courses.taskpage',),
        ),
    ]
