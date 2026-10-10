"""Management command to remove deterministic e2e test fixtures."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from filer.models import Folder
from filer.models.filemodels import File as FilerFile

from experiments.models import Experiment, SubjectData, TrialItem, TrialResult

EXP_IDS = [
    "a0e2e000-0000-0000-0000-000000000001",
    "a0e2e000-0000-0000-0000-000000000002",
    "a0e2e000-0000-0000-0000-000000000003",
    "a0e2e000-0000-0000-0000-000000000004",
    "a0e2e000-0000-0000-0000-000000000005",
    "a0e2e000-0000-0000-0000-000000000006",
]


class Command(BaseCommand):
    """Remove e2e test fixtures created by create_e2e_fixtures."""

    help = "Delete deterministic e2e test fixtures"

    def handle(self, *args, **options):
        """Delete all e2e test objects."""
        TrialResult.objects.filter(subject__experiment_id__in=EXP_IDS).delete()
        SubjectData.objects.filter(experiment_id__in=EXP_IDS).delete()
        # attention_getter is PROTECT, so unlink before the cascade; the
        # (attention_getter, min_dwell_time) constraint needs both cleared
        TrialItem.objects.filter(
            blockitem__outerblockitem__listitem__experiment_id__in=EXP_IDS,
            attention_getter__isnull=False,
        ).update(attention_getter=None, min_dwell_time=None)
        Experiment.objects.filter(id__in=EXP_IDS).delete()
        User.objects.filter(username="e2euser").delete()

        folder = Folder.objects.filter(name="e2e-fixtures").first()
        if folder:
            for filer_file in FilerFile.objects.filter(folder=folder):
                filer_file.file.delete(save=False)
                filer_file.delete()
            folder.delete()

        self.stdout.write(self.style.SUCCESS("e2e fixtures deleted"))
