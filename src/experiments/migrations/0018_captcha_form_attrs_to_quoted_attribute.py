"""Replace the bare ``{{captcha_form_attrs}}`` token with a quoted HTML attribute.

TinyMCE's HTML sanitizer strips bare, unquoted tokens sitting inside a tag's
attribute list (they aren't valid ``name`` or ``name="value"`` syntax), so any
admin who edited ``demographic_data_page_tpl`` through the WYSIWYG editor
silently lost the CAPTCHA form marker. A normal quoted attribute survives.
"""

import logging

from django.db import migrations

logger = logging.getLogger(__name__)

OLD = "{{captcha_form_attrs}}"
NEW = 'data-captcha-provider="{{captcha_provider_name}}"'


def forward(apps, schema_editor):
    Experiment = apps.get_model("experiments", "Experiment")
    updated = []
    for exp in Experiment.objects.all():
        tpl = exp.demographic_data_page_tpl
        if OLD in tpl:
            exp.demographic_data_page_tpl = tpl.replace(OLD, NEW)
            updated.append(exp)
        elif "{{captcha_widget}}" in tpl and "data-captcha-provider" not in tpl:
            logger.warning(
                "Experiment %s uses CAPTCHA placeholders but has no form "
                "marker (old or new). Manual update may be needed.",
                exp.pk,
            )
    if updated:
        Experiment.objects.bulk_update(updated, ["demographic_data_page_tpl"])


def reverse(apps, schema_editor):
    Experiment = apps.get_model("experiments", "Experiment")
    updated = []
    for exp in Experiment.objects.all():
        tpl = exp.demographic_data_page_tpl
        if NEW in tpl:
            exp.demographic_data_page_tpl = tpl.replace(NEW, OLD)
            updated.append(exp)
    if updated:
        Experiment.objects.bulk_update(updated, ["demographic_data_page_tpl"])


class Migration(migrations.Migration):
    dependencies = [
        ("experiments", "0017_alter_experiment_demographic_data_page_tpl"),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=reverse),
    ]
