# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0018_video'),
    ]

    operations = [
        migrations.CreateModel(
            name='CheckboxTaskAnswer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('task', models.ForeignKey(to='courses.CheckboxTask', to_field='taskpage_ptr')),
                ('correct', models.BooleanField(default=None)),
                ('answer', models.TextField()),
                ('hint', models.TextField(blank=True)),
                ('videohint', models.ForeignKey(blank=True, to='courses.Video', to_field='id', null=True)),
                ('comment', models.TextField(verbose_name='Extra comment given upon selection of this answer', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
