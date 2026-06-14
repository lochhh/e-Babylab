import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('experiments', '0008_update_recaptcha_to_enterprise'),
    ]

    operations = [
        migrations.AlterField(
            model_name='experiment',
            name='instrument',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='experiments.instrument',
            ),
        ),
    ]
