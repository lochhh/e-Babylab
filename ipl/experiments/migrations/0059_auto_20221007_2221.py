# Generated by Django 3.1.14 on 2022-10-07 20:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('experiments', '0058_auto_20221007_2220'),
    ]

    operations = [
        migrations.AddField(
            model_name='trialresult',
            name='end_time',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trialresult',
            name='start_time',
            field=models.FloatField(blank=True, null=True),
        ),
    ]