# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0006_lecturepage'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskPage',
            fields=[
                ('contentpage_ptr', models.OneToOneField(to='courses.ContentPage', auto_created=True, primary_key=True, serialize=False, to_field='id')),
                ('question', models.TextField()),
            ],
            options={
            },
            bases=('courses.contentpage',),
        ),
    ]
