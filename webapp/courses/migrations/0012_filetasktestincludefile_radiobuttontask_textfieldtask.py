# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
import courses.models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0011_filetasktestcommand'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileTaskTestIncludeFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('test', models.ForeignKey(to='courses.FileTaskTest', to_field='id')),
                ('name', models.CharField(verbose_name='File name during test', max_length=200)),
                ('purpose', models.CharField(verbose_name='Used as', choices=[('Files given to the program for reading', (('INPUT', 'Input file'),)), ('Files the program is expected to generate', (('OUTPUT', 'Expected output file'),)), ('Executable files', (('REFERENCE', 'Reference implementation'), ('INPUTGEN', 'Input generator'), ('TEST', 'Unit test')))], max_length=10, default='REFERENCE')),
                ('chown_settings', models.CharField(verbose_name='File user ownership', choices=[('OWNED', 'Owned by the tested program'), ('NOT_OWNED', 'Not owned by the tested program')], max_length=10, default='OWNED')),
                ('chgrp_settings', models.CharField(verbose_name='File group ownership', choices=[('OWNED', 'Owned by the tested program'), ('NOT_OWNED', 'Not owned by the tested program')], max_length=10, default='OWNED')),
                ('chmod_settings', models.CharField(verbose_name='File access mode', max_length=10, default='rw-rw-rw-')),
                ('fileinfo', models.FileField(upload_to=courses.models.get_testfile_path)),
            ],
            options={
                'verbose_name': 'included file',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RadiobuttonTask',
            fields=[
                ('taskpage_ptr', models.OneToOneField(auto_created=True, serialize=False, to='courses.TaskPage', primary_key=True, to_field='contentpage_ptr')),
            ],
            options={
            },
            bases=('courses.taskpage',),
        ),
        migrations.CreateModel(
            name='TextfieldTask',
            fields=[
                ('taskpage_ptr', models.OneToOneField(auto_created=True, serialize=False, to='courses.TaskPage', primary_key=True, to_field='contentpage_ptr')),
            ],
            options={
            },
            bases=('courses.taskpage',),
        ),
    ]
