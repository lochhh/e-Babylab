# Generated by Django 3.1.7 on 2021-03-19 13:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('experiments', '0054_auto_20210319_1452'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cdiresult',
            name='given_label',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='item'),
        ),
    ]