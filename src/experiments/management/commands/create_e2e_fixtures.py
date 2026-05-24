"""Management command to seed deterministic e2e test fixtures."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from filebrowser.base import FileObject

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

            TrialItem.objects.get_or_create(
                blockitem=block,
                label="e2e-trial",
                defaults={
                    "code": "E2E1",
                    "visual_onset": 0,
                    "audio_onset": 0,
                    "audio_file": "",
                    # Path need not exist — trial div still renders
                    "visual_file": FileObject("uploads/e2e-test/placeholder.jpg"),
                    "user_input": "NO",
                    "max_duration": 1500,
                    "record_media": False,
                    "record_gaze": False,
                    "is_calibration": False,
                    "calibration_points": [],
                    "position": 1,
                },
            )

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
