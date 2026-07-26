"""Unit tests for experiments/import_export.py."""

import io
import json
import zipfile

import pytest
from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from filer.models import Folder
from filer.models.filemodels import File as FilerFile
from filer.models.imagemodels import Image as FilerImage

from experiments.import_export import _resolve_media, export_to_zip, import_from_zip
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
    """Minimal stand-in for an ``HttpRequest`` exposing only ``.user``."""

    def __init__(self, user):
        """Store *user* as the request's user."""
        self.user = user


def _make_zip_with_media(files_meta):
    """Build a minimal ZIP containing media entries matching *files_meta*."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for meta in files_meta.values():
            zf.writestr(meta["zip_path"], b"content")
    buf.seek(0)
    return zipfile.ZipFile(buf, "r")


# ---------------------------------------------------------------------------
# _resolve_media tests
# ---------------------------------------------------------------------------


class TestResolveMedia:
    """Tests for the ``_resolve_media`` all-or-nothing reuse strategy."""

    @pytest.fixture(autouse=True)
    def _root(self, db):
        self.root, _ = Folder.objects.get_or_create(name="resolve-root", parent=None)

    @pytest.fixture
    def owner(self, db):
        from django.contrib.auth.models import User

        return User.objects.create_user(username="resolver", password="pass")

    @pytest.mark.django_db
    def test_empty_files_meta_returns_empty(self, owner):
        zf = _make_zip_with_media({})
        assert _resolve_media({}, self.root, "sub", zf, owner) == {}
        zf.close()

    @pytest.mark.django_db
    def test_all_found_reuses_existing(self, owner):
        existing = FilerFile(original_filename="a.csv", folder=self.root)
        existing.file.save("a.csv", ContentFile(b"data"), save=True)

        meta = {
            "99": {
                "original_filename": "a.csv",
                "zip_path": "media/99_a.csv",
                "is_image": False,
            }
        }
        zf = _make_zip_with_media(meta)
        result = _resolve_media(meta, self.root, "sub", zf, owner)
        zf.close()

        assert result == {"99": str(existing.pk)}

    @pytest.mark.django_db
    def test_all_found_in_subfolder_reuses(self, owner):
        sub, _ = Folder.objects.get_or_create(name="child", parent=self.root)
        existing = FilerFile(original_filename="b.csv", folder=sub)
        existing.file.save("b.csv", ContentFile(b"data"), save=True)

        meta = {
            "50": {
                "original_filename": "b.csv",
                "zip_path": "media/50_b.csv",
                "is_image": False,
            }
        }
        zf = _make_zip_with_media(meta)
        result = _resolve_media(meta, self.root, "target", zf, owner)
        zf.close()

        assert result == {"50": str(existing.pk)}

    @pytest.mark.django_db
    def test_missing_file_creates_all_fresh(self, owner):
        meta = {
            "10": {
                "original_filename": "x.csv",
                "zip_path": "media/10_x.csv",
                "is_image": False,
            },
            "20": {
                "original_filename": "y.csv",
                "zip_path": "media/20_y.csv",
                "is_image": False,
            },
        }
        zf = _make_zip_with_media(meta)
        result = _resolve_media(meta, self.root, "fresh", zf, owner)
        zf.close()

        assert set(result.keys()) == {"10", "20"}
        folder = Folder.objects.get(name="fresh", parent=self.root)
        for new_pk in result.values():
            obj = FilerFile.objects.get(pk=int(new_pk))
            assert obj.folder == folder
            assert obj.owner == owner

    @pytest.mark.django_db
    def test_partial_match_creates_all_fresh(self, owner):
        existing = FilerFile(original_filename="found.csv", folder=self.root)
        existing.file.save("found.csv", ContentFile(b"data"), save=True)

        meta = {
            "1": {
                "original_filename": "found.csv",
                "zip_path": "media/1_found.csv",
                "is_image": False,
            },
            "2": {
                "original_filename": "missing.csv",
                "zip_path": "media/2_missing.csv",
                "is_image": False,
            },
        }
        zf = _make_zip_with_media(meta)
        result = _resolve_media(meta, self.root, "partial", zf, owner)
        zf.close()

        assert set(result.keys()) == {"1", "2"}
        folder = Folder.objects.get(name="partial", parent=self.root)
        for new_pk in result.values():
            assert FilerFile.objects.get(pk=int(new_pk)).folder == folder

    @pytest.mark.django_db
    def test_image_files_create_filer_image(self, owner):
        meta = {
            "5": {
                "original_filename": "pic.png",
                "zip_path": "media/5_pic.png",
                "is_image": True,
            },
        }
        zf = _make_zip_with_media(meta)
        result = _resolve_media(meta, self.root, "imgs", zf, owner)
        zf.close()

        obj = FilerFile.objects.get(pk=int(result["5"]))
        assert isinstance(obj, FilerImage)


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------


class TestExportToZip:
    """Tests for ``export_to_zip``."""

    @pytest.mark.django_db
    def test_export_produces_zip(
        self,
        experiment_factory,
        filer_file_factory,
        blockitem_factory,
        trialitem_factory,
    ):
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

        for key in (
            "experiment",
            "lists",
            "outerblocks",
            "innerblocks",
            "trials",
            "questions",
            "consentquestions",
            "media_files",
        ):
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
        self,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        filer_file_factory,
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
    """Tests for ``import_from_zip``."""

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
    def test_import_creates_experiment(self, experiment_factory, mock_request):
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
        self,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        filer_file_factory,
        mock_request,
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
        created_file = FilerFile.objects.filter(
            original_filename="cat.mp4", folder=exp_folder
        ).first()
        assert created_file is not None
        assert created_file.owner == mock_request.user
        imported_trial = TrialItem.objects.exclude(pk=trial.pk).first()
        assert imported_trial.visual_file is not None
        assert imported_trial.visual_file.original_filename == "cat.mp4"

    @pytest.mark.django_db
    def test_import_reuses_file_in_experiments_root(
        self,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        mock_request,
    ):
        """File already in experiments/ root is reused — no duplicate created."""
        existing = FilerFile(original_filename="dog.mp4", folder=self.experiments_root)
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

        assert (
            FilerFile.objects.filter(original_filename="dog.mp4").count()
            == before_count
        )

    @pytest.mark.django_db
    def test_import_reuses_file_in_exp_subfolder(
        self,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        mock_request,
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

        assert (
            FilerFile.objects.filter(original_filename="bird.wav").count()
            == before_count
        )

    @pytest.mark.django_db
    def test_import_reuses_file_in_unrelated_subfolder(
        self,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        mock_request,
    ):
        """All files found under experiments/ (any subfolder) → all reused."""
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

        assert (
            FilerFile.objects.filter(original_filename="stim.mp4").count()
            == before_count
        )

    @pytest.mark.django_db
    def test_import_partial_match_creates_all_fresh(
        self,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        filer_file_factory,
        mock_request,
    ):
        """If any file is missing from experiments/, all files are created fresh."""
        exp = experiment_factory(exp_name="PartialMatch")
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        block = blockitem_factory(outerblock=ob)
        trial = trialitem_factory(blockitem=block)
        audio = filer_file_factory("audio.wav")
        visual = filer_file_factory("visual.mp4")
        trial.audio_file = audio
        trial.visual_file = visual
        trial.save()

        zip_bytes = export_to_zip(exp.pk)

        # Keep audio in experiments/ but delete visual — partial match.
        audio_in_root = FilerFile(
            original_filename="audio.wav", folder=self.experiments_root
        )
        audio_in_root.file.save("audio.wav", ContentFile(b"audio"), save=True)
        visual.delete()

        import_from_zip(mock_request, zip_bytes)

        # Both files should have been (re)created fresh under experiments/<exp_name>/.
        # The folder uses the original exp_name from the ZIP, not the copy-suffixed
        # name.
        exp_folder = Folder.objects.get(
            name="PartialMatch", parent=self.experiments_root
        )
        assert FilerFile.objects.filter(
            original_filename="audio.wav", folder=exp_folder
        ).exists()
        assert FilerFile.objects.filter(
            original_filename="visual.mp4", folder=exp_folder
        ).exists()

    @pytest.mark.django_db
    def test_import_duplicate_zip_renames_experiment(
        self, experiment_factory, mock_request
    ):
        """Importing the same ZIP twice creates two experiments with distinct names."""
        exp = experiment_factory(exp_name="DoubleImport")
        zip_bytes = export_to_zip(exp.pk)

        import_from_zip(mock_request, zip_bytes)
        import_from_zip(mock_request, zip_bytes)

        names = set(Experiment.objects.values_list("exp_name", flat=True))
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
        self,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        filer_file_factory,
        mock_request,
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
        count_after_first = FilerFile.objects.filter(
            original_filename="unique.mp4"
        ).count()
        import_from_zip(mock_request, zip_bytes)
        count_after_second = FilerFile.objects.filter(
            original_filename="unique.mp4"
        ).count()

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
        # Collect instrument file PKs, then delete instrument AND its files
        # to simulate cross-database import where old filer PKs don't exist.
        instr_file_pks = [
            getattr(instr, f"{f}_id")
            for f in Instrument._CSV_FILE_FIELDS
            if getattr(instr, f"{f}_id") is not None
        ]
        Instrument.objects.filter(instr_name="new-instr").delete()
        FilerFile.objects.filter(pk__in=instr_file_pks).delete()

        import_from_zip(mock_request, zip_bytes)

        assert Instrument.objects.filter(instr_name="new-instr").exists()
        recreated = Instrument.objects.get(instr_name="new-instr")
        instruments_root = Folder.objects.get(name="instruments", parent=None)
        instr_folder = Folder.objects.get(name="new-instr", parent=instruments_root)
        assert instr_folder.owner == mock_request.user
        for field in Instrument._CSV_FILE_FIELDS:
            filer_file = getattr(recreated, field)
            assert filer_file is not None
            assert filer_file.folder == instr_folder
            assert filer_file.owner == mock_request.user

    @pytest.mark.django_db
    def test_import_instrument_files_not_in_experiments_folder(
        self, experiment_factory, instrument_factory, mock_request
    ):
        """Instrument CSV files are stored under instruments/, not experiments/."""
        instr = instrument_factory(instr_name="folder-check")
        exp = experiment_factory(exp_name="FolderCheck")
        exp.instrument = instr
        exp.save()

        zip_bytes = export_to_zip(exp.pk)
        instr_file_pks = [
            getattr(instr, f"{f}_id")
            for f in Instrument._CSV_FILE_FIELDS
            if getattr(instr, f"{f}_id") is not None
        ]
        Instrument.objects.filter(instr_name="folder-check").delete()
        FilerFile.objects.filter(pk__in=instr_file_pks).delete()

        import_from_zip(mock_request, zip_bytes)

        # No CSV files should land under experiments/
        exp_files = FilerFile.objects.filter(
            folder__parent=self.experiments_root
        ) | FilerFile.objects.filter(folder=self.experiments_root)
        csv_filenames = {f.original_filename for f in exp_files}
        for field in Instrument._CSV_FILE_FIELDS:
            recreated = Instrument.objects.get(instr_name="folder-check")
            filer_file = getattr(recreated, field)
            assert filer_file.original_filename not in csv_filenames

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

        assert (
            Instrument.objects.filter(instr_name="reuse-instr").count() == before_count
        )
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
    def test_import_missing_sharing_group_defaults_to_public(
        self, experiment_factory, mock_request
    ):
        """Sharing group absent on this instance → sharing defaults to public."""
        group = Group.objects.create(name="missing-group")
        exp = experiment_factory(exp_name="GroupShared")
        exp.sharing_option = Experiment.MEMBERSONLY
        exp.sharing_groups.set([group])
        exp.save()

        zip_bytes = export_to_zip(exp.pk)
        group.delete()

        import_from_zip(mock_request, zip_bytes)

        imported = Experiment.objects.filter(
            user=mock_request.user, exp_name="GroupShared copy"
        ).first()
        assert imported is not None
        assert imported.sharing_option == Experiment.PUBLIC
        assert imported.sharing_groups.count() == 0

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
        with pytest.raises(ValueError, match=r"experiment\.json not found"):
            import_from_zip(mock_request, buf.getvalue())
