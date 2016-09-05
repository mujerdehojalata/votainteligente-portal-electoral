# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-08-23 20:30
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('elections', '0027_auto_20160818_1538'),
        ('popular_proposal', '0007_popularproposal_clasification'),
    ]

    operations = [
        migrations.CreateModel(
            name='Commitment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('detail', models.CharField(blank=True, max_length=1024, null=True)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='elections.Candidate')),
                ('proposal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='popular_proposal.PopularProposal')),
            ],
        ),
    ]
