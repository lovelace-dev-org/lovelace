# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CalendarReservation',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('calendar_date', models.ForeignKey(to='courses.CalendarDate', to_field='id')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, to_field='id')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContentPage',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('url_name', models.CharField(editable=False, max_length=200)),
                ('short_name', models.CharField(max_length=32)),
                ('content', models.TextField(null=True, blank=True)),
                ('maxpoints', models.IntegerField(null=True, blank=True)),
                ('access_count', models.IntegerField(null=True, blank=True, editable=False)),
                ('tags', models.TextField(null=True, blank=True)),
                ('require_correct_embedded_tasks', models.BooleanField(default=True, verbose_name='Embedded tasks must be answered correctly to mark this task correct')),
                ('feedback_questions', models.ManyToManyField(null=True, blank=True, to='courses.ContentFeedbackQuestion')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
