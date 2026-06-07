"""Management command to remove deterministic e2e test fixtures."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from experiments.models import Experiment, SubjectData, TrialResult

SUBJECT_IDS = [
    "b0e2e000-0000-0000-0000-000000000001",
    "b0e2e000-0000-0000-0000-000000000002",
    "b0e2e000-0000-0000-0000-000000000003",
    "b0e2e000-0000-0000-0000-000000000004",
    "b0e2e000-0000-0000-0000-000000000005",
]
EXP_IDS = [
    "a0e2e000-0000-0000-0000-000000000001",
    "a0e2e000-0000-0000-0000-000000000002",
    "a0e2e000-0000-0000-0000-000000000003",
    "a0e2e000-0000-0000-0000-000000000004",
    "a0e2e000-0000-0000-0000-000000000005",
]


class Command(BaseCommand):
    """Remove e2e test fixtures created by create_e2e_fixtures."""

    help = "Delete deterministic e2e test fixtures"

    def handle(self, *args, **options):
        """Delete all e2e test objects."""
        TrialResult.objects.filter(subject_id__in=SUBJECT_IDS).delete()
        SubjectData.objects.filter(id__in=SUBJECT_IDS).delete()
        Experiment.objects.filter(id__in=EXP_IDS).delete()
        User.objects.filter(username="e2euser").delete()

        self.stdout.write(self.style.SUCCESS("e2e fixtures deleted"))
