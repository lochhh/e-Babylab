"""Replace provider-specific Turnstile HTML in stored experiment templates with generic CAPTCHA placeholders."""

import logging

from django.db import migrations

logger = logging.getLogger(__name__)

REPLACEMENTS = [
    (
        'data-turnstile-site-key="{{turnstile_site_key}}"',
        "{{captcha_form_attrs}}",
    ),
    (
        '<div class="cf-turnstile turnstile-badge" data-sitekey="{{turnstile_site_key}}" '
        'data-size="compact" data-execution="execute" '
        'data-callback="onTurnstileVerified"></div>',
        "{{captcha_widget}}",
    ),
    (
        "<script src='https://challenges.cloudflare.com/turnstile/v0/api.js' async defer></script>\n",
        "",
    ),
    (
        """<script type="module" src="{% static 'experiments/js/turnstile-handler.js' %}"></script>""",
        "{{captcha_scripts}}",
    ),
]

REVERSE_REPLACEMENTS = [(new, old) for old, new in reversed(REPLACEMENTS)]


def _apply(tpl, replacements):
    for old, new in replacements:
        tpl = tpl.replace(old, new)
    return tpl


def forward(apps, schema_editor):
    Experiment = apps.get_model("experiments", "Experiment")
    updated = []
    for exp in Experiment.objects.all():
        new_tpl = _apply(exp.demographic_data_page_tpl, REPLACEMENTS)
        if new_tpl != exp.demographic_data_page_tpl:
            exp.demographic_data_page_tpl = new_tpl
            updated.append(exp)
        elif "cf-turnstile" in exp.demographic_data_page_tpl:
            logger.warning(
                "Experiment %s has Turnstile HTML but replacement did not match "
                "(possibly customised template). Manual update may be needed.",
                exp.pk,
            )
    if updated:
        Experiment.objects.bulk_update(updated, ["demographic_data_page_tpl"])


def reverse(apps, schema_editor):
    Experiment = apps.get_model("experiments", "Experiment")
    updated = []
    for exp in Experiment.objects.all():
        new_tpl = _apply(exp.demographic_data_page_tpl, REVERSE_REPLACEMENTS)
        if new_tpl != exp.demographic_data_page_tpl:
            exp.demographic_data_page_tpl = new_tpl
            updated.append(exp)
    if updated:
        Experiment.objects.bulk_update(updated, ["demographic_data_page_tpl"])


class Migration(migrations.Migration):
    dependencies = [
        ("experiments", "0015_alter_experiment_information_page_tpl"),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=reverse),
    ]
