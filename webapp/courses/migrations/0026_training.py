# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0025_contentgraph_userradiobuttontaskanswer'),
    ]

    operations = [
        migrations.CreateModel(
            name='Training',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('frontpage', models.ForeignKey(blank=True, to='courses.LecturePage', to_field='contentpage_ptr', null=True)),
                ('start_date', models.DateTimeField(verbose_name='Date and time after which the training is available', blank=True, null=True)),
                ('end_date', models.DateTimeField(verbose_name='Date and time on which the training becomes obsolete', blank=True, null=True)),
                ('contents', models.ManyToManyField(blank=True, to='courses.ContentGraph', null=True)),
                ('responsible', models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('staff', models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('students', models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
