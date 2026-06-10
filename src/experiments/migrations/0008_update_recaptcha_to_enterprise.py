from django.db import migrations

OLD_URL = "https://www.google.com/recaptcha/api.js"
NEW_URL = "https://www.google.com/recaptcha/enterprise.js"

GRECAPTCHA_METHODS = [
    "execute",
    "getResponse",
    "ready",
    "render",
    "reset",
]


def _replace_recaptcha(tpl):
    """Apply all reCAPTCHA Enterprise replacements to a template string."""
    tpl = tpl.replace(OLD_URL, NEW_URL)
    for method in GRECAPTCHA_METHODS:
        tpl = tpl.replace(f"grecaptcha.{method}(", f"grecaptcha.enterprise.{method}(")
    return tpl


def _revert_recaptcha(tpl):
    """Revert all reCAPTCHA Enterprise replacements in a template string."""
    tpl = tpl.replace(NEW_URL, OLD_URL)
    for method in GRECAPTCHA_METHODS:
        tpl = tpl.replace(f"grecaptcha.enterprise.{method}(", f"grecaptcha.{method}(")
    return tpl


def update_recaptcha_to_enterprise(apps, schema_editor):
    """Replace reCAPTCHA api.js URL and method calls with Enterprise equivalents."""
    Experiment = apps.get_model("experiments", "Experiment")
    updated = []
    for exp in Experiment.objects.all():
        new_tpl = _replace_recaptcha(exp.demographic_data_page_tpl)
        if new_tpl != exp.demographic_data_page_tpl:
            exp.demographic_data_page_tpl = new_tpl
            updated.append(exp)
    if updated:
        Experiment.objects.bulk_update(updated, ["demographic_data_page_tpl"])


def reverse_recaptcha_to_enterprise(apps, schema_editor):
    """Revert reCAPTCHA Enterprise URL and method calls back to standard equivalents."""
    Experiment = apps.get_model("experiments", "Experiment")
    updated = []
    for exp in Experiment.objects.all():
        new_tpl = _revert_recaptcha(exp.demographic_data_page_tpl)
        if new_tpl != exp.demographic_data_page_tpl:
            exp.demographic_data_page_tpl = new_tpl
            updated.append(exp)
    if updated:
        Experiment.objects.bulk_update(updated, ["demographic_data_page_tpl"])


class Migration(migrations.Migration):
    """Update existing Experiment records to use reCAPTCHA Enterprise script URL and API calls."""

    dependencies = [
        ("experiments", "0007_update_template_script_tags"),
    ]

    operations = [
        migrations.RunPython(
            update_recaptcha_to_enterprise,
            reverse_code=reverse_recaptcha_to_enterprise,
        ),
    ]
