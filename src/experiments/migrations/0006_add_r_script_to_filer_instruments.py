import os

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import migrations


def add_r_script_to_filer(apps, schema_editor):
    """Register the bundled R script as a filer File in the instruments folder."""
    Folder = apps.get_model("filer", "Folder")
    File = apps.get_model("filer", "File")

    instruments_folder, _ = Folder.objects.get_or_create(name="instruments", parent=None)

    script_name = "generateInstrumentFiles.r"
    script_storage_path = f"instruments/{script_name}"
    script_abs_path = os.path.join(settings.MEDIA_ROOT, "uploads", script_storage_path)
    file_size = os.path.getsize(script_abs_path) if os.path.exists(script_abs_path) else None

    file_ct = ContentType.objects.get(app_label="filer", model="file")

    File.objects.get_or_create(
        folder=instruments_folder,
        original_filename=script_name,
        defaults={
            "file": script_storage_path,
            "name": script_name,
            "_file_size": file_size,
            "is_public": True,
            "mime_type": "text/plain",
            "polymorphic_ctype_id": file_ct.id,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("experiments", "0005_create_default_filer_folders"),
    ]

    operations = [
        migrations.RunPython(add_r_script_to_filer, migrations.RunPython.noop),
    ]
