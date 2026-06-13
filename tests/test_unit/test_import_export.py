"""Unit tests for experiments/import_export.py."""

import io
import json
import zipfile

import pytest
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from filer.models import Folder
from filer.models.filemodels import File as FilerFile
from filer.models.imagemodels import Image as FilerImage

from experiments.import_export import export_to_zip, import_from_zip
from experiments.models import Experiment, Instrument, TrialItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_zip(zip_bytes):
    buf = io.BytesIO(zip_bytes)
    zf = zipfile.ZipFile(buf, "r")
    return zf, json.loads(zf.read("experiment.json").decode())


def _make_experiments_root(db):
    folder, _ = Folder.objects.get_or_create(name="experiments", parent=None)
    return folder


class MockRequest:
    def __init__(self, user):
        self.user = user


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------


class TestExportToZip:
    @pytest.mark.django_db
    def test_export_produces_zip(self, experiment_factory, filer_file_factory, blockitem_factory, trialitem_factory):
        """Export returns valid ZIP bytes."""
        exp = experiment_factory()
        block = blockitem_factory()
        trial = trialitem_factory(blockitem=block)
        trial.visual_file = filer_file_factory("stim.mp4")
        trial.save()

        zip_bytes = export_to_zip(exp.pk)

        assert zip_bytes[:2] == b"PK"
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert "experiment.json" in zf.namelist()

    @pytest.mark.django_db
    def test_export_json_structure(self, experiment_factory):
        """experiment.json contains all required top-level keys."""
        exp = experiment_factory()
        zf, data = _parse_zip(export_to_zip(exp.pk))
        zf.close()

        for key in ("experiment", "lists", "outerblocks", "innerblocks",
                    "trials", "questions", "consentquestions", "media_files"):
            assert key in data

    @pytest.mark.django_db
    def test_export_no_media_files(self, experiment_factory):
        """Experiment with no media → media_files is empty, no media/ entries."""
        exp = experiment_factory()
        zf, data = _parse_zip(export_to_zip(exp.pk))
        names = zf.namelist()
        zf.close()

        assert data["media_files"] == {}
        assert not any(n.startswith("media/") for n in names)

    @pytest.mark.django_db
    def test_export_bundles_trial_media(
        self, experiment_factory, listitem_factory, outerblock_factory,
        blockitem_factory, trialitem_factory, filer_file_factory
    ):
        """audio_file and visual_file are bundled in the ZIP."""
        exp = experiment_factory()
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        block = blockitem_factory(outerblock=ob)
        trial = trialitem_factory(blockitem=block)
        audio = filer_file_factory("sound.wav")
        visual = filer_file_factory("img.png")
        trial.audio_file = audio
        trial.visual_file = visual
        trial.save()

        zf, data = _parse_zip(export_to_zip(exp.pk))
        names = zf.namelist()
        zf.close()

        assert str(audio.pk) in data["media_files"]
        assert str(visual.pk) in data["media_files"]
        assert any(f"_{audio.original_filename}" in n for n in names)
        assert any(f"_{visual.original_filename}" in n for n in names)

    @pytest.mark.django_db
    def test_export_includes_instrument(self, experiment_factory, instrument_factory):
        """Instrument is serialized and all 14 CSV files are bundled."""
        instr = instrument_factory()
        exp = experiment_factory()
        exp.instrument = instr
        exp.save()

        zf, data = _parse_zip(export_to_zip(exp.pk))
        names = zf.namelist()
        zf.close()

        assert "instrument" in data
        assert data["instrument"][0]["fields"]["instr_name"] == instr.instr_name
        # All 14 CSV filer files should appear in media_files and as ZIP entries
        assert len(data["media_files"]) == 14
        assert sum(1 for n in names if n.startswith("media/")) == 14

    @pytest.mark.django_db
    def test_export_no_instrument(self, experiment_factory):
        """Experiment without CDI instrument → no 'instrument' key."""
        exp = experiment_factory()
        _, data = _parse_zip(export_to_zip(exp.pk))
        assert "instrument" not in data

    @pytest.mark.django_db
    def test_export_loading_image(self, experiment_factory, filer_file_factory):
        """loading_image is bundled and marked is_image=True."""
        exp = experiment_factory()
        # Create a FilerImage for loading_image
        img_folder, _ = Folder.objects.get_or_create(name="experiments", parent=None)
        img = FilerImage(original_filename="loading.png", folder=img_folder)
        img.file.save("loading.png", ContentFile(b"\x89PNG"), save=True)
        exp.loading_image = img
        exp.save()

        zf, data = _parse_zip(export_to_zip(exp.pk))
        zf.close()

        pk_str = str(img.pk)
        assert pk_str in data["media_files"]
        assert data["media_files"][pk_str]["is_image"] is True


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------


class TestImportFromZip:
    @pytest.fixture(autouse=True)
    def _experiments_root(self, db):
        self.experiments_root = _make_experiments_root(db)

    @pytest.fixture
    def request_user(self, db):
        return User.objects.create_user(username="importer", password="pass")

    @pytest.fixture
    def mock_request(self, request_user):
        return MockRequest(user=request_user)

    def _make_zip(self, exp, extra_setup=None):
        """Export exp to ZIP bytes (convenience wrapper)."""
        if extra_setup:
            extra_setup(exp)
        return export_to_zip(exp.pk)

    @pytest.mark.django_db
    def test_import_creates_experiment(
        self, experiment_factory, mock_request
    ):
        """Importing a ZIP creates a new Experiment owned by the request user."""
        exp = experiment_factory(exp_name="Alpha")
        zip_bytes = export_to_zip(exp.pk)

        import_from_zip(mock_request, zip_bytes)

        assert Experiment.objects.count() == 2
        imported = Experiment.objects.filter(user=mock_request.user).first()
        assert imported is not None
        assert imported.exp_name == "Alpha copy"

    @pytest.mark.django_db
    def test_import_creates_filer_files_in_exp_folder(
        self, experiment_factory, listitem_factory, outerblock_factory,
        blockitem_factory, trialitem_factory, filer_file_factory, mock_request
    ):
        """Filer files are created under experiments/<exp_name>/ when absent."""
        exp = experiment_factory(exp_name="TestExp")
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        block = blockitem_factory(outerblock=ob)
        trial = trialitem_factory(blockitem=block)
        trial.visual_file = filer_file_factory("cat.mp4")
        trial.save()

        zip_bytes = export_to_zip(exp.pk)

        # Delete original filer file so import must create a new one
        trial.visual_file.delete()

        import_from_zip(mock_request, zip_bytes)

        exp_folder = Folder.objects.get(name="TestExp", parent=self.experiments_root)
        assert FilerFile.objects.filter(
            original_filename="cat.mp4", folder=exp_folder
        ).exists()
        imported_trial = TrialItem.objects.exclude(pk=trial.pk).first()
        assert imported_trial.visual_file is not None
        assert imported_trial.visual_file.original_filename == "cat.mp4"

    @pytest.mark.django_db
    def test_import_reuses_file_in_experiments_root(
        self, experiment_factory, listitem_factory, outerblock_factory,
        blockitem_factory, trialitem_factory, mock_request
    ):
        """File already in experiments/ root is reused — no duplicate created."""
        existing = FilerFile(
            original_filename="dog.mp4", folder=self.experiments_root
        )
        existing.file.save("dog.mp4", ContentFile(b"video"), save=True)
        before_count = FilerFile.objects.filter(original_filename="dog.mp4").count()

        exp = experiment_factory(exp_name="RootReuse")
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        block = blockitem_factory(outerblock=ob)
        trial = trialitem_factory(blockitem=block)
        trial.visual_file = existing
        trial.save()

        zip_bytes = export_to_zip(exp.pk)
        import_from_zip(mock_request, zip_bytes)

        assert FilerFile.objects.filter(original_filename="dog.mp4").count() == before_count

    @pytest.mark.django_db
    def test_import_reuses_file_in_exp_subfolder(
        self, experiment_factory, listitem_factory, outerblock_factory,
        blockitem_factory, trialitem_factory, mock_request
    ):
        """File already in experiments/<exp_name>/ is reused — no duplicate."""
        sub_folder, _ = Folder.objects.get_or_create(
            name="SubReuse", parent=self.experiments_root
        )
        existing = FilerFile(original_filename="bird.wav", folder=sub_folder)
        existing.file.save("bird.wav", ContentFile(b"audio"), save=True)

        exp = experiment_factory(exp_name="SubReuse")
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        block = blockitem_factory(outerblock=ob)
        trial = trialitem_factory(blockitem=block)
        trial.audio_file = existing
        trial.save()

        zip_bytes = export_to_zip(exp.pk)
        before_count = FilerFile.objects.filter(original_filename="bird.wav").count()
        import_from_zip(mock_request, zip_bytes)

        assert FilerFile.objects.filter(original_filename="bird.wav").count() == before_count

    @pytest.mark.django_db
    def test_import_reuses_file_in_unrelated_subfolder(
        self, experiment_factory, listitem_factory, outerblock_factory,
        blockitem_factory, trialitem_factory, mock_request
    ):
        """File stored under experiments/<other_dir>/ on the source is reused if
        a file with the same original_filename exists anywhere under experiments/."""
        other_folder, _ = Folder.objects.get_or_create(
            name="other-stimuli", parent=self.experiments_root
        )
        existing = FilerFile(original_filename="stim.mp4", folder=other_folder)
        existing.file.save("stim.mp4", ContentFile(b"bytes"), save=True)

        exp = experiment_factory(exp_name="UnrelatedDir")
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        block = blockitem_factory(outerblock=ob)
        trial = trialitem_factory(blockitem=block)
        trial.visual_file = existing
        trial.save()

        zip_bytes = export_to_zip(exp.pk)
        before_count = FilerFile.objects.filter(original_filename="stim.mp4").count()
        import_from_zip(mock_request, zip_bytes)

        assert FilerFile.objects.filter(original_filename="stim.mp4").count() == before_count

    @pytest.mark.django_db
    def test_import_duplicate_zip_renames_experiment(
        self, experiment_factory, mock_request
    ):
        """Importing the same ZIP twice creates two experiments with distinct names."""
        exp = experiment_factory(exp_name="DoubleImport")
        zip_bytes = export_to_zip(exp.pk)

        import_from_zip(mock_request, zip_bytes)
        import_from_zip(mock_request, zip_bytes)

        names = set(
            Experiment.objects.values_list("exp_name", flat=True)
        )
        assert "DoubleImport" in names
        assert "DoubleImport copy" in names

    @pytest.mark.django_db
    def test_import_triple_zip_renames_incrementally(
        self, experiment_factory, mock_request
    ):
        """Third import appends 'copy 1' when 'copy' already exists."""
        exp = experiment_factory(exp_name="Triple")
        zip_bytes = export_to_zip(exp.pk)

        import_from_zip(mock_request, zip_bytes)
        import_from_zip(mock_request, zip_bytes)

        names = set(Experiment.objects.values_list("exp_name", flat=True))
        assert "Triple" in names
        assert "Triple copy" in names
        assert "Triple copy 1" in names

    @pytest.mark.django_db
    def test_import_duplicate_zip_no_duplicate_filer_files(
        self, experiment_factory, listitem_factory, outerblock_factory,
        blockitem_factory, trialitem_factory, filer_file_factory, mock_request
    ):
        """Importing same ZIP twice does not duplicate filer files."""
        exp = experiment_factory(exp_name="NoDupFiles")
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        block = blockitem_factory(outerblock=ob)
        trial = trialitem_factory(blockitem=block)
        trial.visual_file = filer_file_factory("unique.mp4")
        trial.save()

        zip_bytes = export_to_zip(exp.pk)
        trial.visual_file.delete()

        import_from_zip(mock_request, zip_bytes)
        count_after_first = FilerFile.objects.filter(original_filename="unique.mp4").count()
        import_from_zip(mock_request, zip_bytes)
        count_after_second = FilerFile.objects.filter(original_filename="unique.mp4").count()

        assert count_after_first == count_after_second == 1

    @pytest.mark.django_db
    def test_import_creates_instrument_when_missing(
        self, experiment_factory, instrument_factory, mock_request
    ):
        """Missing instrument is created with correct name and CSV filer files."""
        instr = instrument_factory(instr_name="new-instr")
        exp = experiment_factory(exp_name="WithInstr")
        exp.instrument = instr
        exp.save()

        zip_bytes = export_to_zip(exp.pk)
        # Remove instrument so import must recreate it
        Instrument.objects.filter(instr_name="new-instr").delete()

        import_from_zip(mock_request, zip_bytes)

        assert Instrument.objects.filter(instr_name="new-instr").exists()
        recreated = Instrument.objects.get(instr_name="new-instr")
        for field in Instrument._CSV_FILE_FIELDS:
            assert getattr(recreated, field) is not None

    @pytest.mark.django_db
    def test_import_reuses_existing_instrument(
        self, experiment_factory, instrument_factory, mock_request
    ):
        """Existing instrument with same name is reused — no duplicate created."""
        instr = instrument_factory(instr_name="reuse-instr")
        exp = experiment_factory(exp_name="ReuseInstr")
        exp.instrument = instr
        exp.save()

        zip_bytes = export_to_zip(exp.pk)
        before_count = Instrument.objects.filter(instr_name="reuse-instr").count()

        import_from_zip(mock_request, zip_bytes)

        assert Instrument.objects.filter(instr_name="reuse-instr").count() == before_count
        imported_exp = Experiment.objects.filter(
            user=mock_request.user, exp_name="ReuseInstr copy"
        ).first()
        assert imported_exp is not None
        assert imported_exp.instrument == instr

    @pytest.mark.django_db
    def test_import_null_media_fields(self, experiment_factory, mock_request):
        """ZIP with empty media_files imports successfully with null media fields."""
        exp = experiment_factory(exp_name="NullMedia")
        zip_bytes = export_to_zip(exp.pk)

        import_from_zip(mock_request, zip_bytes)

        imported = Experiment.objects.filter(
            user=mock_request.user, exp_name="NullMedia copy"
        ).first()
        assert imported is not None
        assert imported.loading_image is None

    @pytest.mark.django_db
    def test_import_invalid_zip_raises(self, mock_request):
        """Non-ZIP bytes raise ValueError with a descriptive message."""
        with pytest.raises(ValueError, match="not a valid ZIP"):
            import_from_zip(mock_request, b"this is not a zip file")

    @pytest.mark.django_db
    def test_import_zip_missing_experiment_json_raises(self, mock_request):
        """ZIP without experiment.json raises ValueError with a descriptive message."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("other.txt", "irrelevant")
        with pytest.raises(ValueError, match="experiment.json not found"):
            import_from_zip(mock_request, buf.getvalue())
