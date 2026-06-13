from django.db import migrations

REPLACEMENTS = [
    (
        'data-recaptcha-site-key="{{recaptcha_site_key}}"',
        'data-turnstile-site-key="{{turnstile_site_key}}"',
    ),
    (
        "<!-- reCAPTCHA input -->\n                        "
        '<input type="hidden" id="g-recaptcha-response" name="g-recaptcha-response">',
        '<div class="cf-turnstile" data-sitekey="{{turnstile_site_key}}" data-size="invisible" data-callback="onTurnstileVerified"></div>',
    ),
    (
        "<!-- reCAPTCHA API -->\n"
        "<script src='https://www.google.com/recaptcha/enterprise.js?render={{recaptcha_site_key}}'></script>",
        "<script src='https://challenges.cloudflare.com/turnstile/v0/api.js' async defer></script>",
    ),
    (
        "recaptcha-handler.js",
        "turnstile-handler.js",
    ),
]

REVERSE_REPLACEMENTS = [(new, old) for old, new in reversed(REPLACEMENTS)]


def _apply(tpl, replacements):
    for old, new in replacements:
        tpl = tpl.replace(old, new)
    return tpl


def update_to_turnstile(apps, schema_editor):
    Experiment = apps.get_model("experiments", "Experiment")
    updated = []
    for exp in Experiment.objects.all():
        new_tpl = _apply(exp.demographic_data_page_tpl, REPLACEMENTS)
        if new_tpl != exp.demographic_data_page_tpl:
            exp.demographic_data_page_tpl = new_tpl
            updated.append(exp)
    if updated:
        Experiment.objects.bulk_update(updated, ["demographic_data_page_tpl"])


def revert_to_recaptcha(apps, schema_editor):
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
    """Replace Google reCAPTCHA Enterprise with Cloudflare Turnstile in stored experiment templates."""

    dependencies = [
        ("experiments", "0008_update_recaptcha_to_enterprise"),
    ]

    operations = [
        migrations.RunPython(update_to_turnstile, reverse_code=revert_to_recaptcha),
    ]
