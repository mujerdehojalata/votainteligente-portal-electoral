# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-11-29 21:29
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('elections', '0030_election_candidates_can_commit_everywhere'),
    ]

    operations = [
        migrations.AddField(
            model_name='election',
            name='second_round',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='elections.Election'),
        ),
    ]
