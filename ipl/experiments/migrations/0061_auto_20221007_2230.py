# Generated by Django 3.1.14 on 2022-10-07 20:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('experiments', '0060_startendtimes_to_float'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='trialresult',
            name='end_time_old',
        ),
        migrations.RemoveField(
            model_name='trialresult',
            name='start_time_old',
        ),
    ]