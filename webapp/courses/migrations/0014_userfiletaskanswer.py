# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0013_useranswer'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserFileTaskAnswer',
            fields=[
                ('useranswer_ptr', models.OneToOneField(auto_created=True, serialize=False, to='courses.UserAnswer', primary_key=True, to_field='id')),
                ('task', models.ForeignKey(to='courses.FileTask', to_field='taskpage_ptr')),
                ('returnable', models.OneToOneField(to='courses.FileTaskReturnable', to_field='id')),
            ],
            options={
            },
            bases=('courses.useranswer',),
        ),
    ]
