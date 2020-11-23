# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-09-24 12:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('figures', '0011_add_mau_to_site_daily_metrics'),
    ]

    operations = [
        migrations.AddField(
            model_name='learnercoursegrademetrics',
            name='letter_grade',
            field=models.CharField(blank=True, default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='learnercoursegrademetrics',
            name='passed_timestamp',
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='learnercoursegrademetrics',
            name='percent_grade',
            field=models.FloatField(default=0.0),
        ),
    ]