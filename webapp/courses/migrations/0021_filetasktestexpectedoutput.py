# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0020_filetasktestexpectederror'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileTaskTestExpectedOutput',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('test', models.ForeignKey(to='courses.FileTaskTest', to_field='id')),
                ('correct', models.BooleanField(default=None)),
                ('regexp', models.BooleanField(default=None)),
                ('expected_answer', models.TextField(blank=True)),
                ('hint', models.TextField(blank=True)),
                ('videohint', models.ForeignKey(blank=True, to='courses.Video', to_field='id', null=True)),
            ],
            options={
                'verbose_name': 'expected output',
            },
            bases=(models.Model,),
        ),
    ]
