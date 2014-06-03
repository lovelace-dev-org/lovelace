# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0016_userprofile'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserTextfieldTaskAnswer',
            fields=[
                ('useranswer_ptr', models.OneToOneField(auto_created=True, serialize=False, to='courses.UserAnswer', primary_key=True, to_field='id')),
                ('task', models.ForeignKey(to='courses.TextfieldTask', to_field='taskpage_ptr')),
                ('given_answer', models.TextField()),
            ],
            options={
            },
            bases=('courses.useranswer',),
        ),
    ]
