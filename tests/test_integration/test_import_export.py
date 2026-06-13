"""Integration tests for experiment export/import HTTP views."""

import io
import zipfile

import pytest
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.urls import reverse
from filer.models import Folder
from filer.models.filemodels import File as FilerFile

from experiments.import_export import export_to_zip
from experiments.models import Experiment


def _make_experiments_root():
    folder, _ = Folder.objects.get_or_create(name="experiments", parent=None)
    return folder


class TestExperimentExportView:
    @pytest.mark.django_db
    def test_returns_zip_response(self, client, experiment_factory):
        """GET experiment_export returns a valid ZIP with correct headers."""
        exp = experiment_factory()
        url = reverse("experiments:experimentExport", args=[exp.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert response["Content-Type"] == "application/zip"
        assert response["Content-Disposition"].endswith('.zip"')
        assert response.content[:2] == b"PK"

    @pytest.mark.django_db
    def test_zip_contains_experiment_json(self, client, experiment_factory):
        """The returned ZIP contains a valid experiment.json."""
        exp = experiment_factory()
        url = reverse("experiments:experimentExport", args=[exp.pk])
        response = client.get(url)

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            assert "experiment.json" in zf.namelist()

    @pytest.mark.django_db
    def test_filename_matches_experiment_name(self, client, experiment_factory):
        """Content-Disposition filename matches the experiment's exp_name."""
        exp = experiment_factory(exp_name="My Exp")
        url = reverse("experiments:experimentExport", args=[exp.pk])
        response = client.get(url)

        assert '"My Exp.zip"' in response["Content-Disposition"]

    @pytest.mark.django_db
    def test_404_for_missing_experiment(self, client):
        """Non-existent experiment UUID returns 404."""
        url = reverse(
            "experiments:experimentExport",
            args=["00000000-0000-0000-0000-000000000000"],
        )
        response = client.get(url)
        assert response.status_code == 404


class TestExperimentImportView:
    @pytest.fixture(autouse=True)
    def _experiments_root(self, db):
        _make_experiments_root()

    @pytest.mark.django_db
    def test_get_renders_import_form(self, client):
        """GET experiment_import renders the import form."""
        url = reverse("experiments:experimentImport")
        response = client.get(url)

        assert response.status_code == 200
        assert b"import_file" in response.content

    @pytest.mark.django_db
    def test_post_zip_creates_experiment_and_redirects(
        self, client, experiment_factory, user
    ):
        """POSTing a valid ZIP creates a new experiment and redirects to the list."""
        exp = experiment_factory(exp_name="ImportMe")
        zip_bytes = export_to_zip(exp.pk)

        client.force_login(user)
        url = reverse("experiments:experimentImport")
        response = client.post(
            url,
            {"import_file": io.BytesIO(zip_bytes)},
        )

        assert response.status_code == 302
        assert response["Location"] == "/admin/experiments/experiment"
        assert Experiment.objects.filter(exp_name="ImportMe copy").exists()

    @pytest.mark.django_db
    def test_post_zip_with_media_files(
        self, client, experiment_factory, listitem_factory, outerblock_factory,
        blockitem_factory, trialitem_factory, filer_file_factory, user
    ):
        """Importing a ZIP with media creates the filer files and links them."""
        exp = experiment_factory(exp_name="MediaImport")
        li = listitem_factory(experiment=exp)
        ob = outerblock_factory(listitem=li)
        block = blockitem_factory(outerblock=ob)
        trial = trialitem_factory(blockitem=block)
        trial.visual_file = filer_file_factory("stim.mp4")
        trial.save()

        zip_bytes = export_to_zip(exp.pk)
        trial.visual_file.delete()

        client.force_login(user)
        url = reverse("experiments:experimentImport")
        client.post(url, {"import_file": io.BytesIO(zip_bytes)})

        assert FilerFile.objects.filter(original_filename="stim.mp4").exists()
        from experiments.models import TrialItem
        imported_trial = TrialItem.objects.exclude(pk=trial.pk).first()
        assert imported_trial is not None
        assert imported_trial.visual_file is not None

    @pytest.mark.django_db
    def test_post_invalid_form_rerenders(self, client):
        """POST with no file re-renders the form (no redirect)."""
        url = reverse("experiments:experimentImport")
        response = client.post(url, {})

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_post_invalid_zip_shows_error(self, client):
        """POST with a non-ZIP file re-renders the form with a field error."""
        url = reverse("experiments:experimentImport")
        from django.core.files.uploadedfile import SimpleUploadedFile

        bad_file = SimpleUploadedFile("bad.zip", b"not a zip", content_type="application/zip")
        response = client.post(url, {"import_file": bad_file})

        assert response.status_code == 200
        assert b"not a valid ZIP" in response.content

    @pytest.mark.django_db
    def test_post_zip_missing_experiment_json_shows_error(self, client):
        """POST with a ZIP lacking experiment.json re-renders with a field error."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("other.txt", "irrelevant")

        url = reverse("experiments:experimentImport")
        from django.core.files.uploadedfile import SimpleUploadedFile

        bad_zip = SimpleUploadedFile("bad.zip", buf.getvalue(), content_type="application/zip")
        response = client.post(url, {"import_file": bad_zip})

        assert response.status_code == 200
        assert b"experiment.json not found" in response.content
