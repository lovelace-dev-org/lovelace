# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
import courses.models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0009_filetask'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileTaskTest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('task', models.ForeignKey(to='courses.FileTask', to_field='taskpage_ptr')),
                ('name', models.CharField(verbose_name='Test name', max_length=200)),
                ('timeout', models.TimeField(default=courses.models.default_timeout)),
                ('signals', models.CharField(choices=[('None', "Don't send any signals"), ('SIGINT', 'Interrupt signal (same as Ctrl-C)')], max_length=7, default='None')),
                ('inputs', models.TextField(verbose_name='Input given to the main command through STDIN', blank=True)),
                ('retval', models.IntegerField(verbose_name='Expected return value', blank=True, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
