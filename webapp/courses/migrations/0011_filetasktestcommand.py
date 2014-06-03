# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0010_filetasktest'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileTaskTestCommand',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('test', models.ForeignKey(to='courses.FileTaskTest', to_field='id')),
                ('command_line', models.CharField(max_length=500)),
                ('main_command', models.BooleanField(verbose_name='Command which receives the specified input', default=None)),
            ],
            options={
                'verbose_name': 'UNIX command to run for the test',
                'verbose_name_plural': 'UNIX commands to run for the test',
            },
            bases=(models.Model,),
        ),
    ]
