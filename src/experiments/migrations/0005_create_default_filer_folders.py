from django.db import migrations


def create_default_folders(apps, schema_editor):
    Folder = apps.get_model("filer", "Folder")
    for name in ("experiments", "instruments"):
        Folder.objects.get_or_create(name=name, parent=None)


class Migration(migrations.Migration):
    dependencies = [
        ("experiments", "0004_alter_experiment_loading_image_and_more"),
        ("filer", "0018_alter_file_options"),
    ]

    operations = [
        migrations.RunPython(create_default_folders, migrations.RunPython.noop),
    ]
