# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0024_usercheckboxtaskanswer'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserRadiobuttonTaskAnswer',
            fields=[
                ('useranswer_ptr', models.OneToOneField(auto_created=True, serialize=False, to='courses.UserAnswer', primary_key=True, to_field='id')),
                ('task', models.ForeignKey(to='courses.RadiobuttonTask', to_field='taskpage_ptr')),
                ('chosen_answer', models.ForeignKey(to='courses.RadiobuttonTaskAnswer', to_field='id')),
            ],
            options={
            },
            bases=('courses.useranswer',),
        ),
        migrations.CreateModel(
            name='ContentGraph',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('content', models.ForeignKey(blank=True, to='courses.ContentPage', to_field='id', null=True)),
                ('compulsory', models.BooleanField(verbose_name='Must be answered correctly before proceeding to next task', default=False)),
                ('deadline', models.DateTimeField(verbose_name='The due date for completing this task', blank=True, null=True)),
                ('publish_date', models.DateTimeField(verbose_name='When does this task become available', blank=True, null=True)),
                ('scored', models.BooleanField(verbose_name='Does this task affect scoring', default=True)),
                ('responsible', models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
