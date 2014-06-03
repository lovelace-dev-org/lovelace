# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0005_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='LecturePage',
            fields=[
                ('contentpage_ptr', models.OneToOneField(to='courses.ContentPage', auto_created=True, primary_key=True, serialize=False, to_field='id')),
                ('answerable', models.BooleanField(default=False, verbose_name='Need confirmation of reading this lecture')),
            ],
            options={
            },
            bases=('courses.contentpage',),
        ),
    ]
