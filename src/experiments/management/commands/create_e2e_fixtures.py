"""Management command to seed deterministic e2e test fixtures."""

import io
import wave as _wave

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from filer.models import Folder
from filer.models.filemodels import File as FilerFile

from experiments.models import (
    BlockItem,
    Experiment,
    ListItem,
    OuterBlockItem,
    SubjectData,
    TrialItem,
    TrialResult,
)

MODES = [
    (
        "a0e2e000-0000-0000-0000-000000000001",
        "b0e2e000-0000-0000-0000-000000000001",
        "NON",
    ),
    (
        "a0e2e000-0000-0000-0000-000000000002",
        "b0e2e000-0000-0000-0000-000000000002",
        "AUD",
    ),
    (
        "a0e2e000-0000-0000-0000-000000000003",
        "b0e2e000-0000-0000-0000-000000000003",
        "VID",
    ),
    (
        "a0e2e000-0000-0000-0000-000000000004",
        "b0e2e000-0000-0000-0000-000000000004",
        "EYE",
    ),
    (
        "a0e2e000-0000-0000-0000-000000000005",
        "b0e2e000-0000-0000-0000-000000000005",
        "ALL",
    ),
]

# Minimal 1x1 white pixel PNG (valid, browser-renderable)
_PLACEHOLDER_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\xd7c\xf8\xcf\xc0\x00\x00\x00"
    b"\x02\x00\x01\xe2!\xbc3"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _make_silent_wav(duration_ms=100):
    """Return bytes for a short silent mono WAV file."""
    buf = io.BytesIO()
    with _wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * int(8000 * duration_ms / 1000))
    return buf.getvalue()


def _get_or_create_filer_file(filename, content, folder):
    """Return an existing filer File in folder, or create one with the given content."""
    existing = FilerFile.objects.filter(
        original_filename=filename, folder=folder
    ).first()
    if existing:
        return existing
    f = FilerFile(original_filename=filename, folder=folder)
    f.file.save(filename, ContentFile(content), save=True)
    return f


class Command(BaseCommand):
    """Create or refresh e2e test fixtures for all recording modes."""

    help = "Create deterministic e2e test fixtures (idempotent)"

    def handle(self, *args, **options):
        """Create all e2e test objects idempotently."""
        subject_ids = [s for _, s, _ in MODES]
        TrialResult.objects.filter(subject_id__in=subject_ids).delete()

        user, _ = User.objects.get_or_create(
            username="e2euser",
            defaults={
                "email": "e2e@test.local",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        user.set_password("e2epass")
        user.save()

        folder, _ = Folder.objects.get_or_create(name="e2e-fixtures")
        visual_file = _get_or_create_filer_file(
            "e2e-placeholder.png", _PLACEHOLDER_PNG, folder
        )
        audio_file = _get_or_create_filer_file(
            "e2e-placeholder.wav", _make_silent_wav(), folder
        )

        for exp_id, subject_id, mode in MODES:
            experiment, _ = Experiment.objects.get_or_create(
                id=exp_id,
                defaults={
                    "user": user,
                    "exp_name": f"e2e-{mode.lower()}",
                    "recording_option": mode,
                    "include_pause_page": False,
                    "list_selection_strategy": "SEQ",
                    "show_gaze_estimations": False,
                    "general_onset": 0,
                },
            )

            listitem, _ = ListItem.objects.get_or_create(
                experiment=experiment,
                list_name="e2e-list",
                defaults={"global_timeout": 300000, "exclude_list": False},
            )

            outer_block, _ = OuterBlockItem.objects.get_or_create(
                listitem=listitem,
                outer_block_name="e2e-outer",
                defaults={"position": 1, "randomise_inner_blocks": False},
            )

            block, _ = BlockItem.objects.get_or_create(
                outerblockitem=outer_block,
                label="e2e-block",
                defaults={
                    "background_colour": "#FFFFFF",
                    "randomise_trials": False,
                    "position": 1,
                },
            )

            trial, created = TrialItem.objects.get_or_create(
                blockitem=block,
                label="e2e-trial",
                defaults={
                    "code": "E2E1",
                    "visual_onset": 0,
                    "audio_onset": 0,
                    "audio_file": audio_file,
                    "visual_file": visual_file,
                    "user_input": "NO",
                    "max_duration": 1500,
                    "record_media": False,
                    "record_gaze": False,
                    "is_calibration": False,
                    "calibration_points": [],
                    "position": 1,
                },
            )
            if not created:
                trial.visual_file = visual_file
                trial.audio_file = audio_file
                trial.save(update_fields=["visual_file", "audio_file"])

            SubjectData.objects.get_or_create(
                id=subject_id,
                defaults={
                    "experiment": experiment,
                    "listitem": listitem,
                    "participant_id": 9000 + MODES.index((exp_id, subject_id, mode)),
                },
            )

        self.stdout.write(
            self.style.SUCCESS("e2e fixtures created for all 5 recording modes")
        )
