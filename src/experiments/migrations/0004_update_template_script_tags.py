from django.db import migrations


REPLACEMENTS = [
    (
        "browser_check_page_tpl",
        "<script src=\"{% static 'experiments/js/browser-check.js' %}\"></script>",
        "<script type=\"module\" src=\"{% static 'experiments/js/browser-check.js' %}\"></script>",
    ),
    (
        "webcam_check_page_tpl",
        "<script src=\"{% static 'experiments/js/webcam-calibration.js' %}\"></script>",
        "<script type=\"module\" src=\"{% static 'experiments/js/webcam-calibration.js' %}\"></script>",
    ),
    (
        "microphone_check_page_tpl",
        "<script src=\"{% static 'experiments/js/webcam-calibration.js' %}\"></script>",
        "<script type=\"module\" src=\"{% static 'experiments/js/webcam-calibration.js' %}\"></script>",
    ),
    (
        "thank_you_page_tpl",
        "<script src=\"{% static 'experiments/js/endpage.js' %}\"></script>",
        "<script type=\"module\" src=\"{% static 'experiments/js/endpage.js' %}\"></script>",
    ),
    (
        "thank_you_abort_page_tpl",
        "<script src=\"{% static 'experiments/js/endpage.js' %}\"></script>",
        "<script type=\"module\" src=\"{% static 'experiments/js/endpage.js' %}\"></script>",
    ),
    (
        "demographic_data_page_tpl",
        "<script src=\"{% static 'experiments/js/recaptcha-handler.js' %}\"></script>",
        "<script type=\"module\" src=\"{% static 'experiments/js/resolution.js' %}\"></script>\n"
        "    <script type=\"module\" src=\"{% static 'experiments/js/recaptcha-handler.js' %}\"></script>",
    ),
]

EXPERIMENT_PAGE_OLD = (
    "<script src=\"{% static 'experiments/js/experiment.js' %}\"></script>\n"
    "<script src=\"{% static 'experiments/js/webgazer.min.js' %}\"></script>\n"
    "<script src=\"{% static 'experiments/js/webgazer-calibration.js' %}\"></script>"
)

EXPERIMENT_PAGE_NEW = (
    "<script src=\"{% static 'experiments/js/webgazer.min.js' %}\"></script>\n"
    "    <script type=\"module\" src=\"{% static 'experiments/js/experiment.js' %}\"></script>"
)


def update_template_script_tags(apps, schema_editor):
    """Update Experiment template fields to use ES module script tags."""
    Experiment = apps.get_model("experiments", "Experiment")
    updated = []
    for exp in Experiment.objects.all():
        changed = False
        for field, old, new in REPLACEMENTS:
            value = getattr(exp, field)
            if old in value:
                setattr(exp, field, value.replace(old, new))
                changed = True
        value = exp.experiment_page_tpl
        if EXPERIMENT_PAGE_OLD in value:
            exp.experiment_page_tpl = value.replace(EXPERIMENT_PAGE_OLD, EXPERIMENT_PAGE_NEW)
            changed = True
        if changed:
            updated.append(exp)
    if updated:
        Experiment.objects.bulk_update(
            updated,
            [
                "browser_check_page_tpl",
                "webcam_check_page_tpl",
                "microphone_check_page_tpl",
                "thank_you_page_tpl",
                "thank_you_abort_page_tpl",
                "demographic_data_page_tpl",
                "experiment_page_tpl",
            ],
        )


def reverse_template_script_tags(apps, schema_editor):
    """No-op reverse for template script tag migration."""
    pass


class Migration(migrations.Migration):
    """Update existing Experiment records to use ES module script tags."""

    dependencies = [
        ("experiments", "0003_alter_experiment_browser_check_page_tpl_and_more"),
    ]

    operations = [
        migrations.RunPython(
            update_template_script_tags,
            reverse_code=reverse_template_script_tags,
        ),
    ]
