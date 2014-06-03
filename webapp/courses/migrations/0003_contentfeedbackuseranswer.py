# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0002_calendarreservation_contentpage'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentFeedbackUserAnswer',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, to_field='id')),
                ('content', models.ForeignKey(to='courses.ContentPage', to_field='id')),
                ('question', models.ForeignKey(to='courses.ContentFeedbackQuestion', to_field='id')),
                ('rating', models.PositiveSmallIntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
