# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0023_textfieldtaskanswer'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserCheckboxTaskAnswer',
            fields=[
                ('useranswer_ptr', models.OneToOneField(auto_created=True, serialize=False, to='courses.UserAnswer', primary_key=True, to_field='id')),
                ('task', models.ForeignKey(to='courses.CheckboxTask', to_field='taskpage_ptr')),
                ('chosen_answers', models.ManyToManyField(to='courses.CheckboxTaskAnswer')),
            ],
            options={
            },
            bases=('courses.useranswer',),
        ),
    ]
