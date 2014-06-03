# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0026_training'),
    ]

    operations = [
        migrations.AddField(
            model_name='contentgraph',
            name='parentnode',
            field=models.ForeignKey(blank=True, to='courses.ContentGraph', to_field='id', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='evaluation',
            name='correct',
            field=models.BooleanField(default=None),
        ),
    ]
