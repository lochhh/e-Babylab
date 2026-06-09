import re

from django.db import migrations

# Script files that must be loaded as ES modules.
# webgazer.min.js is a non-module vendor bundle and is intentionally excluded.
MODULE_SCRIPTS = [
    "experiments/js/experiment.js",
    "experiments/js/webgazer-calibration.js",
    "experiments/js/webcam-calibration.js",
    "experiments/js/browser-check.js",
    "experiments/js/endpage.js",
    "experiments/js/recaptcha-handler.js",
    "experiments/js/resolution.js",
]

TEMPLATE_FIELDS = [
    "experiment_page_tpl",
    "webcam_check_page_tpl",
    "microphone_check_page_tpl",
    "browser_check_page_tpl",
    "thank_you_page_tpl",
    "thank_you_abort_page_tpl",
    "demographic_data_page_tpl",
]


def _add_module_type(tpl):
    """Add type="module" to script tags that load known ES module files."""
    for path in MODULE_SCRIPTS:
        # Match <script ...> tags containing this path but lacking type="module".
        # The src attribute value may contain single quotes (e.g. {% static '...' %}),
        # so we match the full tag with [^>]* and check for the path within it.
        tpl = re.sub(
            rf'(<script(?![^>]*type=["\']module["\'])[^>]*{re.escape(path)}[^>]*>)',
            lambda m: m.group(0).replace("<script", '<script type="module"', 1),
            tpl,
        )
    return tpl


def _remove_module_type(tpl):
    """Remove type="module" from script tags that load known ES module files."""
    for path in MODULE_SCRIPTS:
        tpl = re.sub(
            rf'(<script type="module"[^>]*{re.escape(path)}[^>]*>)',
            lambda m: m.group(0).replace(' type="module"', "", 1),
            tpl,
        )
    return tpl


def update_template_script_tags(apps, schema_editor):
    """Update Experiment template fields to use ES module script tags."""
    Experiment = apps.get_model("experiments", "Experiment")
    updated = []
    for exp in Experiment.objects.all():
        changed = False
        for field in TEMPLATE_FIELDS:
            old = getattr(exp, field)
            new = _add_module_type(old)
            if new != old:
                setattr(exp, field, new)
                changed = True
        if changed:
            updated.append(exp)
    if updated:
        Experiment.objects.bulk_update(updated, TEMPLATE_FIELDS)


def reverse_template_script_tags(apps, schema_editor):
    """Revert Experiment template fields to non-module script tags."""
    Experiment = apps.get_model("experiments", "Experiment")
    updated = []
    for exp in Experiment.objects.all():
        changed = False
        for field in TEMPLATE_FIELDS:
            old = getattr(exp, field)
            new = _remove_module_type(old)
            if new != old:
                setattr(exp, field, new)
                changed = True
        if changed:
            updated.append(exp)
    if updated:
        Experiment.objects.bulk_update(updated, TEMPLATE_FIELDS)


class Migration(migrations.Migration):
    """Update existing Experiment records to use ES module script tags."""

    dependencies = [
        ("experiments", "0006_add_r_script_to_filer_instruments"),
    ]

    operations = [
        migrations.RunPython(
            update_template_script_tags,
            reverse_code=reverse_template_script_tags,
        ),
    ]
