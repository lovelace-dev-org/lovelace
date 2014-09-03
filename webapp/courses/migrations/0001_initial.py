# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import courses.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Calendar',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(verbose_name='Name for reference in content', max_length=200, unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CalendarDate',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('event_name', models.CharField(max_length=200, verbose_name='Name of the event')),
                ('event_description', models.CharField(null=True, max_length=200, blank=True, verbose_name='Description')),
                ('start_time', models.DateTimeField(verbose_name='Starts at')),
                ('end_time', models.DateTimeField(verbose_name='Ends at')),
                ('reservable_slots', models.IntegerField(verbose_name='Amount of reservable slots')),
                ('calendar', models.ForeignKey(to='courses.Calendar')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CalendarReservation',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('calendar_date', models.ForeignKey(to='courses.CalendarDate')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CheckboxTaskAnswer',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('correct', models.BooleanField(default=None)),
                ('answer', models.TextField()),
                ('hint', models.TextField(blank=True)),
                ('comment', models.TextField(verbose_name='Extra comment given upon selection of this answer', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContentFeedbackQuestion',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('question', models.CharField(max_length=100, verbose_name='Question')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContentFeedbackUserAnswer',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('rating', models.PositiveSmallIntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContentGraph',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('compulsory', models.BooleanField(verbose_name='Must be answered correctly before proceeding to next task', default=False)),
                ('deadline', models.DateTimeField(null=True, blank=True, verbose_name='The due date for completing this task')),
                ('publish_date', models.DateTimeField(null=True, blank=True, verbose_name='When does this task become available')),
                ('scored', models.BooleanField(verbose_name='Does this task affect scoring', default=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContentPage',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(help_text='The full name of this page', max_length=200)),
                ('url_name', models.CharField(editable=False, max_length=200)),
                ('short_name', models.CharField(help_text='The short name is used for referring this page on other pages', max_length=32)),
                ('content', models.TextField(null=True, blank=True)),
                ('maxpoints', models.IntegerField(null=True, blank=True)),
                ('access_count', models.IntegerField(null=True, editable=False, blank=True)),
                ('tags', models.TextField(null=True, blank=True)),
                ('require_correct_embedded_tasks', models.BooleanField(verbose_name='Embedded tasks must be answered correctly to mark this task correct', default=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Evaluation',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('correct', models.BooleanField(default=None)),
                ('points', models.FloatField(blank=True)),
                ('feedback', models.CharField(verbose_name='Feedback given by a teacher', max_length=2000, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(verbose_name='Name for reference in content', max_length=200, unique=True)),
                ('date_uploaded', models.DateTimeField(verbose_name='date uploaded')),
                ('typeinfo', models.CharField(max_length=200)),
                ('fileinfo', models.FileField(max_length=255, upload_to=courses.models.get_file_upload_path)),
                ('uploader', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FileTaskReturnable',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
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
            name='FileTaskReturnFile',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('fileinfo', models.FileField(max_length=255, upload_to=courses.models.get_answerfile_path)),
                ('returnable', models.ForeignKey(to='courses.FileTaskReturnable')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FileTaskTest',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(max_length=200, verbose_name='Test name')),
                ('timeout', models.TimeField(default=courses.models.default_timeout)),
                ('signals', models.CharField(choices=[('None', "Don't send any signals"), ('SIGINT', 'Interrupt signal (same as Ctrl-C)')], max_length=7, default='None')),
                ('inputs', models.TextField(verbose_name='Input given to the main command through STDIN', blank=True)),
                ('retval', models.IntegerField(null=True, blank=True, verbose_name='Expected return value')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FileTaskTestCommand',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('command_line', models.CharField(max_length=500)),
                ('main_command', models.BooleanField(verbose_name='Command which receives the specified input', default=None)),
                ('test', models.ForeignKey(to='courses.FileTaskTest')),
            ],
            options={
                'verbose_name_plural': 'UNIX commands to run for the test',
                'verbose_name': 'UNIX command to run for the test',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FileTaskTestExpectedError',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('correct', models.BooleanField(default=None)),
                ('regexp', models.BooleanField(default=None)),
                ('expected_answer', models.TextField(blank=True)),
                ('hint', models.TextField(blank=True)),
                ('test', models.ForeignKey(to='courses.FileTaskTest')),
            ],
            options={
                'verbose_name': 'expected error',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FileTaskTestExpectedOutput',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('correct', models.BooleanField(default=None)),
                ('regexp', models.BooleanField(default=None)),
                ('expected_answer', models.TextField(blank=True)),
                ('hint', models.TextField(blank=True)),
                ('test', models.ForeignKey(to='courses.FileTaskTest')),
            ],
            options={
                'verbose_name': 'expected output',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FileTaskTestIncludeFile',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(max_length=200, verbose_name='File name during test')),
                ('purpose', models.CharField(choices=[('Files given to the program for reading', (('INPUT', 'Input file'),)), ('Files the program is expected to generate', (('OUTPUT', 'Expected output file'),)), ('Executable files', (('REFERENCE', 'Reference implementation'), ('INPUTGEN', 'Input generator'), ('TEST', 'Unit test')))], max_length=10, verbose_name='Used as', default='REFERENCE')),
                ('chown_settings', models.CharField(choices=[('OWNED', 'Owned by the tested program'), ('NOT_OWNED', 'Not owned by the tested program')], max_length=10, verbose_name='File user ownership', default='OWNED')),
                ('chgrp_settings', models.CharField(choices=[('OWNED', 'Owned by the tested program'), ('NOT_OWNED', 'Not owned by the tested program')], max_length=10, verbose_name='File group ownership', default='OWNED')),
                ('chmod_settings', models.CharField(max_length=10, verbose_name='File access mode', default='rw-rw-rw-')),
                ('fileinfo', models.FileField(max_length=255, upload_to=courses.models.get_testfile_path)),
                ('test', models.ForeignKey(to='courses.FileTaskTest')),
            ],
            options={
                'verbose_name': 'included file',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(verbose_name='Name for reference in content', max_length=200, unique=True)),
                ('date_uploaded', models.DateTimeField(verbose_name='date uploaded')),
                ('description', models.CharField(max_length=500)),
                ('fileinfo', models.ImageField(upload_to=courses.models.get_image_upload_path)),
                ('uploader', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LecturePage',
            fields=[
                ('contentpage_ptr', models.OneToOneField(serialize=False, parent_link=True, auto_created=True, to='courses.ContentPage', primary_key=True)),
                ('answerable', models.BooleanField(verbose_name='Need confirmation of reading this lecture', default=False)),
            ],
            options={
            },
            bases=('courses.contentpage',),
        ),
        migrations.CreateModel(
            name='RadiobuttonTaskAnswer',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('correct', models.BooleanField(default=None)),
                ('answer', models.TextField()),
                ('hint', models.TextField(blank=True)),
                ('comment', models.TextField(verbose_name='Extra comment given upon selection of this answer', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TaskPage',
            fields=[
                ('contentpage_ptr', models.OneToOneField(serialize=False, parent_link=True, auto_created=True, to='courses.ContentPage', primary_key=True)),
                ('question', models.TextField()),
            ],
            options={
            },
            bases=('courses.contentpage',),
        ),
        migrations.CreateModel(
            name='RadiobuttonTask',
            fields=[
                ('taskpage_ptr', models.OneToOneField(serialize=False, parent_link=True, auto_created=True, to='courses.TaskPage', primary_key=True)),
            ],
            options={
            },
            bases=('courses.taskpage',),
        ),
        migrations.CreateModel(
            name='FileTask',
            fields=[
                ('taskpage_ptr', models.OneToOneField(serialize=False, parent_link=True, auto_created=True, to='courses.TaskPage', primary_key=True)),
            ],
            options={
            },
            bases=('courses.taskpage',),
        ),
        migrations.CreateModel(
            name='CheckboxTask',
            fields=[
                ('taskpage_ptr', models.OneToOneField(serialize=False, parent_link=True, auto_created=True, to='courses.TaskPage', primary_key=True)),
            ],
            options={
            },
            bases=('courses.taskpage',),
        ),
        migrations.CreateModel(
            name='TextfieldTask',
            fields=[
                ('taskpage_ptr', models.OneToOneField(serialize=False, parent_link=True, auto_created=True, to='courses.TaskPage', primary_key=True)),
            ],
            options={
            },
            bases=('courses.taskpage',),
        ),
        migrations.CreateModel(
            name='TextfieldTaskAnswer',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('correct', models.BooleanField(default=None)),
                ('regexp', models.BooleanField(default=None)),
                ('answer', models.TextField()),
                ('hint', models.TextField(blank=True)),
                ('comment', models.TextField(verbose_name='Extra comment given upon writing matching answer', blank=True)),
                ('task', models.ForeignKey(to='courses.TextfieldTask')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Training',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('start_date', models.DateTimeField(null=True, blank=True, verbose_name='Date and time after which the training is available')),
                ('end_date', models.DateTimeField(null=True, blank=True, verbose_name='Date and time on which the training becomes obsolete')),
                ('contents', models.ManyToManyField(null=True, blank=True, to='courses.ContentGraph')),
                ('frontpage', models.ForeignKey(null=True, blank=True, to='courses.LecturePage')),
                ('responsible', models.ManyToManyField(null=True, related_name='responsiblefor', blank=True, to=settings.AUTH_USER_MODEL)),
                ('staff', models.ManyToManyField(null=True, related_name='staffing', blank=True, to=settings.AUTH_USER_MODEL)),
                ('students', models.ManyToManyField(null=True, related_name='studentin', blank=True, to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserAnswer',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('answer_date', models.DateTimeField(verbose_name='Date and time of when the user answered this task')),
                ('collaborators', models.TextField(null=True, blank=True, verbose_name='Which users was this task answered with')),
                ('checked', models.BooleanField(verbose_name='This answer has been checked', default=False)),
                ('draft', models.BooleanField(verbose_name='This answer is a draft', default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserCheckboxTaskAnswer',
            fields=[
                ('useranswer_ptr', models.OneToOneField(serialize=False, parent_link=True, auto_created=True, to='courses.UserAnswer', primary_key=True)),
                ('chosen_answers', models.ManyToManyField(to='courses.CheckboxTaskAnswer')),
                ('task', models.ForeignKey(to='courses.CheckboxTask')),
            ],
            options={
            },
            bases=('courses.useranswer',),
        ),
        migrations.CreateModel(
            name='UserFileTaskAnswer',
            fields=[
                ('useranswer_ptr', models.OneToOneField(serialize=False, parent_link=True, auto_created=True, to='courses.UserAnswer', primary_key=True)),
                ('returnable', models.OneToOneField(to='courses.FileTaskReturnable')),
                ('task', models.ForeignKey(to='courses.FileTask')),
            ],
            options={
            },
            bases=('courses.useranswer',),
        ),
        migrations.CreateModel(
            name='UserLecturePageAnswer',
            fields=[
                ('useranswer_ptr', models.OneToOneField(serialize=False, parent_link=True, auto_created=True, to='courses.UserAnswer', primary_key=True)),
                ('answered', models.BooleanField(verbose_name=courses.models.LecturePage, default=None)),
                ('task', models.ForeignKey(to='courses.LecturePage')),
            ],
            options={
            },
            bases=('courses.useranswer',),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('student_id', models.IntegerField(null=True, blank=True, verbose_name='Student number')),
                ('study_program', models.CharField(null=True, max_length=80, blank=True, verbose_name='Study program')),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserRadiobuttonTaskAnswer',
            fields=[
                ('useranswer_ptr', models.OneToOneField(serialize=False, parent_link=True, auto_created=True, to='courses.UserAnswer', primary_key=True)),
                ('chosen_answer', models.ForeignKey(to='courses.RadiobuttonTaskAnswer')),
                ('task', models.ForeignKey(to='courses.RadiobuttonTask')),
            ],
            options={
            },
            bases=('courses.useranswer',),
        ),
        migrations.CreateModel(
            name='UserTextfieldTaskAnswer',
            fields=[
                ('useranswer_ptr', models.OneToOneField(serialize=False, parent_link=True, auto_created=True, to='courses.UserAnswer', primary_key=True)),
                ('given_answer', models.TextField()),
                ('task', models.ForeignKey(to='courses.TextfieldTask')),
            ],
            options={
            },
            bases=('courses.useranswer',),
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('link', models.URLField()),
                ('uploader', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='useranswer',
            name='evaluation',
            field=models.OneToOneField(to='courses.Evaluation'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='useranswer',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='textfieldtaskanswer',
            name='videohint',
            field=models.ForeignKey(null=True, blank=True, to='courses.Video'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='radiobuttontaskanswer',
            name='task',
            field=models.ForeignKey(to='courses.RadiobuttonTask'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='radiobuttontaskanswer',
            name='videohint',
            field=models.ForeignKey(null=True, blank=True, to='courses.Video'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='filetasktestexpectedoutput',
            name='videohint',
            field=models.ForeignKey(null=True, blank=True, to='courses.Video'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='filetasktestexpectederror',
            name='videohint',
            field=models.ForeignKey(null=True, blank=True, to='courses.Video'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='filetasktest',
            name='task',
            field=models.ForeignKey(to='courses.FileTask'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contentpage',
            name='feedback_questions',
            field=models.ManyToManyField(null=True, blank=True, to='courses.ContentFeedbackQuestion'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contentgraph',
            name='content',
            field=models.ForeignKey(null=True, blank=True, to='courses.ContentPage'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contentgraph',
            name='parentnode',
            field=models.ForeignKey(null=True, blank=True, to='courses.ContentGraph'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contentgraph',
            name='responsible',
            field=models.ManyToManyField(null=True, blank=True, to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contentfeedbackuseranswer',
            name='content',
            field=models.ForeignKey(to='courses.ContentPage'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contentfeedbackuseranswer',
            name='question',
            field=models.ForeignKey(to='courses.ContentFeedbackQuestion'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contentfeedbackuseranswer',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='checkboxtaskanswer',
            name='task',
            field=models.ForeignKey(to='courses.CheckboxTask'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='checkboxtaskanswer',
            name='videohint',
            field=models.ForeignKey(null=True, blank=True, to='courses.Video'),
            preserve_default=True,
        ),
    ]
