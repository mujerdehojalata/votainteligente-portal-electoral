# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-08-30 21:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('popular_proposal', '0009_auto_20160825_1438'),
    ]

    operations = [
        migrations.AddField(
            model_name='commitment',
            name='commited',
            field=models.NullBooleanField(default=None),
        ),
    ]
