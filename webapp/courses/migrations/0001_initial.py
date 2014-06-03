# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Evaluation',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('correct', models.BooleanField()),
                ('points', models.FloatField(blank=True)),
                ('feedback', models.CharField(blank=True, max_length=2000, verbose_name='Feedback given by a teacher')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Calendar',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(unique=True, max_length=200, verbose_name='Name for reference in content')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FileTaskReturnable',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('run_time', models.TimeField()),
                ('output', models.TextField()),
                ('errors', models.TextField()),
                ('retval', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContentFeedbackQuestion',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('question', models.CharField(max_length=100, verbose_name='Question')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CalendarDate',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('calendar', models.ForeignKey(to='courses.Calendar', to_field='id')),
                ('event_name', models.CharField(max_length=200, verbose_name='Name of the event')),
                ('event_description', models.CharField(null=True, blank=True, max_length=200, verbose_name='Description')),
                ('start_time', models.DateTimeField(verbose_name='Starts at')),
                ('end_time', models.DateTimeField(verbose_name='Ends at')),
                ('reservable_slots', models.IntegerField(verbose_name='Amount of reservable slots')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
