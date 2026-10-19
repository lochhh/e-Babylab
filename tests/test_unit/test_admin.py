"""Unit tests for experiments/admin.py."""

import json
import re
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, User
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.test import RequestFactory, override_settings
from django.urls import reverse
from django.utils import timezone

from experiments.admin import (
    AnswerTextInline,
    BlockItemAdmin,
    CdiResultInline,
    ExperimentAdmin,
    InstrumentAdmin,
    ListItemAdmin,
    OuterBlockItemAdmin,
    QuestionInline,
    SubjectDataAdmin,
    TrialItemInline,
    TrialResultAdmin,
    TrialResultInline,
    eye_off_text,
)
from experiments.models import (
    BlockItem,
    ConsentQuestion,
    Experiment,
    Instrument,
    ListItem,
    OuterBlockItem,
    Question,
    SubjectData,
    TrialItem,
    TrialResult,
)


class MockRequest:
    """Minimal request stub that carries a user attribute."""

    def __init__(self, user=None):
        """Initialise with an optional user."""
        self.user = user


@pytest.fixture
def admin_site():
    """Return a bare AdminSite instance for use in admin class tests."""
    return AdminSite()


@pytest.fixture
def experiment_admin(admin_site):
    """Return an ExperimentAdmin instance bound to the test admin site."""
    return ExperimentAdmin(Experiment, admin_site)


@pytest.fixture
def subject_data_admin(admin_site):
    """Return a SubjectDataAdmin instance bound to the test admin site."""
    return SubjectDataAdmin(SubjectData, admin_site)


@pytest.fixture
def trial_result_admin(admin_site):
    """Return a TrialResultAdmin instance bound to the test admin site."""
    return TrialResultAdmin(TrialResult, admin_site)


@pytest.fixture
def rf():
    """Return a Django RequestFactory instance."""
    return RequestFactory()


# ---------------------------------------------------------------------------
# QuestionInline
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_question_inline_get_formset_obj_none(admin_site, rf, user):
    """Verify get_formset returns a formset class when obj is None."""
    inline = QuestionInline(Experiment, admin_site)
    request = rf.get("/")
    request.user = user

    # obj=None: returns early without setting extra
    formset_class = inline.get_formset(request, obj=None)
    assert formset_class is not None


@pytest.mark.django_db
def test_question_inline_get_formset_no_questions(
    admin_site, experiment_factory, rf, user
):
    """Verify get_formset returns a formset class when experiment has no questions."""
    ex = experiment_factory()
    inline = QuestionInline(Experiment, admin_site)
    request = rf.get("/")
    request.user = user

    # No questions exist: extra should be 2 (default) but still returns a formset
    formset_class = inline.get_formset(request, obj=ex)
    assert formset_class is not None


@pytest.mark.django_db
def test_question_inline_get_formset_with_questions(
    admin_site, experiment_factory, question_factory, rf, user
):
    """Verify get_formset returns a formset class when the experiment has questions."""
    ex = experiment_factory()
    question_factory(experiment=ex)
    inline = QuestionInline(Experiment, admin_site)
    request = rf.get("/")
    request.user = user

    # Questions exist: extra should be 0
    formset_class = inline.get_formset(request, obj=ex)
    assert formset_class is not None


# ---------------------------------------------------------------------------
# AnswerBaseInline
# ---------------------------------------------------------------------------


class TestAnswerBaseInline:
    """Tests for AnswerBaseInline permission methods."""

    def test_has_add_permission_returns_false(self, admin_site):
        """Verify has_add_permission always returns False."""
        inline = AnswerTextInline(SubjectData, admin_site)
        request = MockRequest()
        assert inline.has_add_permission(request) is False
        assert inline.has_add_permission(request, obj=MagicMock()) is False

    def test_has_delete_permission_returns_false(self, admin_site):
        """Verify has_delete_permission always returns False."""
        inline = AnswerTextInline(SubjectData, admin_site)
        request = MockRequest()
        assert inline.has_delete_permission(request) is False
        assert inline.has_delete_permission(request, obj=MagicMock()) is False


# ---------------------------------------------------------------------------
# CdiResultInline
# ---------------------------------------------------------------------------


class TestCdiResultInline:
    """Tests for CdiResultInline permission methods."""

    def test_has_add_permission_returns_false(self, admin_site):
        """Verify has_add_permission always returns False."""
        inline = CdiResultInline(SubjectData, admin_site)
        request = MockRequest()
        assert inline.has_add_permission(request) is False
        assert inline.has_add_permission(request, obj=MagicMock()) is False


# ---------------------------------------------------------------------------
# TrialResultInline
# ---------------------------------------------------------------------------


class TestTrialResultInline:
    """Tests for the TrialResultInline admin helper methods."""

    @pytest.fixture
    def inline(self, admin_site):
        """Return a TrialResultInline instance for testing."""
        return TrialResultInline(SubjectData, admin_site)

    def _make_obj(self, **trialitem_attrs):
        """Build a mock TrialResult with given trialitem attribute overrides."""
        obj = MagicMock()
        for k, v in trialitem_attrs.items():
            setattr(obj.trialitem, k, v)
        return obj

    def test_trial_blockitem(self, inline):
        """Verify trial_blockitem returns the trialitem's blockitem."""
        obj = MagicMock()
        result = inline.trial_blockitem(obj)
        assert result == obj.trialitem.blockitem

    def test_trial_audio(self, inline):
        """Verify trial_audio returns the audio file's original filename."""
        obj = MagicMock()
        obj.trialitem.audio_file.original_filename = "audio.mp3"
        assert inline.trial_audio(obj) == "audio.mp3"

    def test_trial_visual(self, inline):
        """Verify trial_visual returns the visual file's original filename."""
        obj = MagicMock()
        obj.trialitem.visual_file.original_filename = "image.png"
        assert inline.trial_visual(obj) == "image.png"

    def test_trial_input(self, inline):
        """Verify trial_input returns the trialitem's user_input value."""
        obj = MagicMock()
        obj.trialitem.user_input = "KEY"
        assert inline.trial_input(obj) == "KEY"

    def test_trial_maxduration(self, inline):
        """Verify trial_maxduration returns the trialitem's max_duration value."""
        obj = MagicMock()
        obj.trialitem.max_duration = 3000
        assert inline.trial_maxduration(obj) == 3000

    def test_response_time_with_times(self, inline):
        """Verify response_time returns elapsed time string when both times exist."""
        obj = MagicMock()
        obj.start_time = 1000.0
        obj.end_time = 1500.5
        result = inline.response_time(obj)
        assert result == str(1500.5 - 1000.0)

    def test_response_time_missing_times(self, inline):
        """Verify response_time returns an empty string when both times are None."""
        obj = MagicMock()
        obj.start_time = None
        obj.end_time = None
        assert inline.response_time(obj) == ""

    def test_response_time_partial_times(self, inline):
        """Verify response_time returns an empty string when end_time is None."""
        obj = MagicMock()
        obj.start_time = 1000.0
        obj.end_time = None
        assert inline.response_time(obj) == ""

    def test_webcam_file_link_with_file(self, inline):
        """Verify webcam_file_link returns the file name when a webcam file exists."""
        obj = MagicMock()
        obj.webcam_file = MagicMock()
        obj.webcam_file.name = "recordings/video.webm"
        assert inline.webcam_file_link(obj) == "recordings/video.webm"

    def test_webcam_file_link_without_file(self, inline):
        """Verify webcam_file_link returns '-' when no webcam file is attached."""
        obj = MagicMock()
        obj.webcam_file = None
        assert inline.webcam_file_link(obj) == "-"

    def test_has_add_permission_returns_false(self, inline):
        """Verify has_add_permission always returns False."""
        request = MockRequest()
        assert inline.has_add_permission(request) is False
        assert inline.has_add_permission(request, obj=MagicMock()) is False


# ---------------------------------------------------------------------------
# InstrumentAdmin
# ---------------------------------------------------------------------------


class TestInstrumentAdmin:
    """Tests for InstrumentAdmin custom change form rendering."""

    def test_render_change_form_sets_help_text(self, admin_site, rf):
        """Verify render_change_form injects help_text into the context."""
        instrument_admin = InstrumentAdmin(Instrument, admin_site)
        request = rf.get("/")
        context = {}

        with patch.object(admin.ModelAdmin, "render_change_form", return_value=None):
            instrument_admin.render_change_form(request, context)

        assert "help_text" in context
        assert (
            instrument_admin.change_form_template
            == "admin/experiments/change_form_help_text.html"
        )

    def test_render_change_form_sets_template(self, admin_site, rf):
        """Verify render_change_form sets the custom change_form_template path."""
        instrument_admin = InstrumentAdmin(Instrument, admin_site)
        request = rf.get("/")
        context = {}

        with patch.object(admin.ModelAdmin, "render_change_form", return_value=None):
            instrument_admin.render_change_form(request, context)

        assert (
            instrument_admin.change_form_template
            == "admin/experiments/change_form_help_text.html"
        )


# ---------------------------------------------------------------------------
# ExperimentAdmin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExperimentAdmin:
    """Tests for ExperimentAdmin queryset filtering and model save behaviour."""

    def test_save_model_assigns_user_when_none(
        self, experiment_admin, experiment_factory, user, rf
    ):
        """Verify save_model assigns the request user when object has no user set."""
        request = rf.get("/")
        request.user = user
        obj = experiment_factory()
        obj.user = None

        experiment_admin.save_model(request, obj, None, False)
        assert obj.user == user
        assert obj.pk is not None

    def test_save_model_preserves_existing_user(
        self, experiment_admin, experiment_factory, user, rf
    ):
        """Verify save_model does not overwrite a user that is already assigned."""
        other_user = User.objects.create_user(username="other_owner", password="pass")
        request = rf.get("/")
        request.user = user
        obj = experiment_factory()
        obj.user = other_user

        experiment_admin.save_model(request, obj, None, False)
        # User was already set, so it should remain unchanged
        assert obj.user == other_user

    def test_get_queryset_superuser(self, experiment_admin, experiment_factory, rf):
        """Verify superusers see all experiments in the queryset."""
        superuser = User.objects.create_superuser(
            username="admin", password="password", email="admin@test.com"
        )
        ex1 = experiment_factory()
        ex2 = experiment_factory()

        request = rf.get("/")
        request.user = superuser

        qs = experiment_admin.get_queryset(request)
        assert ex1 in qs
        assert ex2 in qs
        assert qs.count() >= 2

    def test_get_queryset_owner(self, experiment_admin, experiment_factory, user, rf):
        """Verify owners see their own experiments but not other private experiments."""
        ex_owned = experiment_factory(exp_name="Owned")
        ex_owned.user = user
        ex_owned.save()

        other_user = User.objects.create_user(username="other", password="password")
        ex_other = experiment_factory(exp_name="Other")
        ex_other.user = other_user
        ex_other.sharing_option = "OWN"
        ex_other.save()

        request = rf.get("/")
        request.user = user

        qs = experiment_admin.get_queryset(request)
        assert ex_owned in qs
        assert ex_other not in qs

    def test_get_queryset_public_visible_to_non_owner(
        self, experiment_admin, experiment_factory, user, rf
    ):
        """Verify public experiments are visible to users who do not own them."""
        other_user = User.objects.create_user(username="pub_owner", password="pass")
        ex_public = experiment_factory(exp_name="Public")
        ex_public.user = other_user
        ex_public.sharing_option = "PUB"
        ex_public.save()

        request = rf.get("/")
        request.user = user

        qs = experiment_admin.get_queryset(request)
        assert ex_public in qs

    def test_get_queryset_shared_group(
        self, experiment_admin, experiment_factory, user, group, rf
    ):
        """Verify group-shared experiments are visible to users in the sharing group."""
        user.groups.add(group)
        other_user = User.objects.create_user(username="other2", password="password")

        ex_shared = experiment_factory(exp_name="Shared")
        ex_shared.user = other_user
        ex_shared.sharing_option = "GRP"
        ex_shared.save()
        ex_shared.sharing_groups.add(group)

        request = rf.get("/")
        request.user = user

        qs = experiment_admin.get_queryset(request)
        assert ex_shared in qs

    def test_get_queryset_group_not_shared_with_user_group(
        self, experiment_admin, experiment_factory, user, rf
    ):
        """Verify group-shared experiments are hidden from out-group users."""
        other_group = Group.objects.create(name="other_group")
        other_user = User.objects.create_user(username="grp_owner", password="pass")

        ex_grp = experiment_factory(exp_name="GroupOnly")
        ex_grp.user = other_user
        ex_grp.sharing_option = "GRP"
        ex_grp.save()
        ex_grp.sharing_groups.add(other_group)

        request = rf.get("/")
        request.user = user  # user is not in other_group

        qs = experiment_admin.get_queryset(request)
        assert ex_grp not in qs

    def test_has_change_permission_no_obj(self, experiment_admin, user, rf):
        """Verify has_change_permission returns True when no object is given."""
        request = rf.get("/")
        request.user = user
        assert experiment_admin.has_change_permission(request) is True

    def test_has_change_permission_owner(
        self, experiment_admin, experiment_factory, user, rf
    ):
        """Verify the experiment owner has change permission."""
        ex = experiment_factory(exp_name="Mine")
        ex.user = user
        ex.save()

        request = rf.get("/")
        request.user = user
        assert experiment_admin.has_change_permission(request, ex) is True

    def test_has_change_permission_non_owner(
        self, experiment_admin, experiment_factory, user, rf
    ):
        """Verify a non-owner user lacks change permission for a private experiment."""
        ex = experiment_factory(exp_name="NotMine")
        ex.sharing_option = "OWN"
        ex.save()

        other_user = User.objects.create_user(username="other3", password="password")
        request = rf.get("/")
        request.user = other_user
        assert experiment_admin.has_change_permission(request, ex) is False

    def test_has_change_permission_public_experiment(
        self, experiment_admin, experiment_factory, user, rf
    ):
        """Verify any user has change permission for a public experiment."""
        ex = experiment_factory(exp_name="Public")
        ex.sharing_option = "PUB"
        ex.save()

        other_user = User.objects.create_user(username="other4", password="pass")
        request = rf.get("/")
        request.user = other_user
        assert experiment_admin.has_change_permission(request, ex) is True

    def test_has_change_permission_group_shared_matching(
        self, experiment_admin, experiment_factory, user, group, rf
    ):
        """Verify a group member has change permission for a group-shared experiment."""
        user.groups.add(group)
        ex = experiment_factory(exp_name="GroupShared")
        ex.sharing_option = "GRP"
        ex.save()
        ex.sharing_groups.add(group)

        request = rf.get("/")
        request.user = user
        assert experiment_admin.has_change_permission(request, ex) is True

    def test_has_change_permission_superuser(
        self, experiment_admin, experiment_factory, rf
    ):
        """Verify superusers have change permission regardless of sharing option."""
        superuser = User.objects.create_superuser(
            username="su", password="pass", email="su@t.com"
        )
        ex = experiment_factory(exp_name="Private")
        ex.sharing_option = "OWN"
        ex.save()

        request = rf.get("/")
        request.user = superuser
        assert experiment_admin.has_change_permission(request, ex) is True

    def test_experiment_buttons(self, experiment_admin, experiment_factory):
        """Verify experiment_buttons returns HTML with the expected action links."""
        ex = experiment_factory()
        buttons_html = experiment_admin.experiment_buttons(ex)

        assert reverse("experiments:informationPage", args=[ex.id]) in buttons_html
        assert "Go to Experiment" in buttons_html
        assert "Download Results" in buttons_html
        assert "Export Experiment" in buttons_html

    def test_export_to_zip_structure(
        self,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
    ):
        """Verify export_to_zip's experiment.json has all expected keys."""
        import io
        import zipfile

        from experiments.import_export import export_to_zip

        ex = experiment_factory()
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)
        ti = trialitem_factory(blockitem=bi)

        zip_bytes = export_to_zip(ex.id)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            data = json.loads(zf.read("experiment.json"))

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

        assert data["experiment"][0]["pk"] == str(ex.id)
        assert data["trials"][0]["pk"] == ti.id

    def test_export_to_zip_includes_questions(
        self, experiment_factory, question_factory, consent_question_factory
    ):
        """Verify export_to_zip separates questions into their keys."""
        import io
        import zipfile

        from experiments.import_export import export_to_zip

        ex = experiment_factory()
        question_factory(experiment=ex, text="Q1")
        consent_question_factory(experiment=ex, text="Consent?")

        zip_bytes = export_to_zip(ex.id)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            data = json.loads(zf.read("experiment.json"))

        assert len(data["questions"]) == 1
        assert len(data["consentquestions"]) == 1

    def test_import_from_zip_creates_new_experiment(self, experiment_factory, user, rf):
        """Verify import_from_zip creates a new experiment owned by the request user."""
        from filer.models import Folder

        from experiments.import_export import export_to_zip, import_from_zip

        Folder.objects.get_or_create(name="experiments", parent=None)

        ex = experiment_factory()
        zip_bytes = export_to_zip(ex.id)

        new_user = User.objects.create_user(username="importer", password="pass")
        request = rf.post("/")
        request.user = new_user

        initial_count = Experiment.objects.count()
        before = timezone.now()
        import_from_zip(request, zip_bytes)
        after = timezone.now()

        assert Experiment.objects.count() == initial_count + 1
        new_exp = Experiment.objects.exclude(pk=ex.pk).first()
        assert new_exp.user == new_user
        assert before <= new_exp.created_on <= after

    def test_import_from_zip_recreates_full_hierarchy(
        self,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
        question_factory,
        consent_question_factory,
        user,
        rf,
    ):
        """Verify import_from_zip recreates the full experiment hierarchy."""
        from filer.models import Folder

        from experiments.import_export import export_to_zip, import_from_zip

        Folder.objects.get_or_create(name="experiments", parent=None)

        ex = experiment_factory()
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)
        trialitem_factory(blockitem=bi)
        question_factory(experiment=ex)
        consent_question_factory(experiment=ex)

        zip_bytes = export_to_zip(ex.id)

        request = rf.post("/")
        request.user = user

        import_from_zip(request, zip_bytes)

        assert Experiment.objects.count() == 2
        assert ListItem.objects.count() == 2
        assert OuterBlockItem.objects.count() == 2
        assert BlockItem.objects.count() == 2
        assert TrialItem.objects.count() == 2
        assert Question.objects.count() == 2
        assert ConsentQuestion.objects.count() == 2

        new_exp = Experiment.objects.exclude(pk=ex.pk).get()
        new_li = ListItem.objects.exclude(pk=li.pk).get()
        new_ob = OuterBlockItem.objects.exclude(pk=ob.pk).get()
        new_bi = BlockItem.objects.exclude(pk=bi.pk).get()

        assert new_li.experiment == new_exp
        assert new_ob.listitem == new_li
        assert new_bi.outerblockitem == new_ob


# ---------------------------------------------------------------------------
# ListItemAdmin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListItemAdmin:
    """Tests for ListItemAdmin queryset filtering and model permission methods."""

    @pytest.fixture
    def list_admin(self, admin_site):
        """Return a ListItemAdmin instance bound to the test admin site."""
        return ListItemAdmin(ListItem, admin_site)

    def test_get_model_perms_returns_empty(self, list_admin, rf, user):
        """Verify get_model_perms returns an empty dict to hide the model from menus."""
        request = rf.get("/")
        request.user = user
        assert list_admin.get_model_perms(request) == {}

    def test_get_queryset_owner(
        self, list_admin, listitem_factory, experiment_factory, user, rf
    ):
        """Verify an owner sees their own experiment's list items."""
        ex = experiment_factory()
        ex.user = user
        ex.save()
        li = listitem_factory(experiment=ex)

        request = rf.get("/")
        request.user = user
        qs = list_admin.get_queryset(request)
        assert li in qs

    def test_get_queryset_superuser(
        self, list_admin, listitem_factory, experiment_factory, rf
    ):
        """Verify superusers see all list items."""
        superuser = User.objects.create_superuser(
            username="su2", password="pass", email="su2@t.com"
        )
        li = listitem_factory()
        request = rf.get("/")
        request.user = superuser
        qs = list_admin.get_queryset(request)
        assert li in qs

    def test_get_queryset_public_visible_to_non_owner(
        self, list_admin, listitem_factory, experiment_factory, user, rf
    ):
        """Verify list items from public experiments are visible to non-owners."""
        other_user = User.objects.create_user(username="li_owner", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "PUB"
        ex.save()
        li = listitem_factory(experiment=ex)

        request = rf.get("/")
        request.user = user
        qs = list_admin.get_queryset(request)
        assert li in qs

    def test_get_queryset_private_hidden_from_non_owner(
        self, list_admin, listitem_factory, experiment_factory, user, rf
    ):
        """Verify list items from private experiments are hidden from non-owners."""
        other_user = User.objects.create_user(username="li_owner2", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "OWN"
        ex.save()
        li = listitem_factory(experiment=ex)

        request = rf.get("/")
        request.user = user
        qs = list_admin.get_queryset(request)
        assert li not in qs

    def test_get_queryset_group_shared(
        self, list_admin, listitem_factory, experiment_factory, user, group, rf
    ):
        """Verify list items from group-shared experiments are visible to members."""
        user.groups.add(group)
        other_user = User.objects.create_user(username="li_grp_owner", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "GRP"
        ex.save()
        ex.sharing_groups.add(group)
        li = listitem_factory(experiment=ex)

        request = rf.get("/")
        request.user = user
        qs = list_admin.get_queryset(request)
        assert li in qs


# ---------------------------------------------------------------------------
# OuterBlockItemAdmin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOuterBlockItemAdmin:
    """Tests for OuterBlockItemAdmin queryset filtering and helper methods."""

    @pytest.fixture
    def ob_admin(self, admin_site):
        """Return an OuterBlockItemAdmin instance bound to the test admin site."""
        return OuterBlockItemAdmin(OuterBlockItem, admin_site)

    def test_get_experiment(
        self, ob_admin, outerblock_factory, listitem_factory, experiment_factory, user
    ):
        """Verify get_experiment returns the experiment for a given outer block."""
        ex = experiment_factory()
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)
        assert ob_admin.get_experiment(ob) == ex

    def test_get_model_perms_returns_empty(self, ob_admin, rf, user):
        """Verify get_model_perms returns an empty dict to hide the model from menus."""
        request = rf.get("/")
        request.user = user
        assert ob_admin.get_model_perms(request) == {}

    def test_get_queryset_owner(
        self,
        ob_admin,
        outerblock_factory,
        listitem_factory,
        experiment_factory,
        user,
        rf,
    ):
        """Verify owners see outer block items from their own experiments."""
        ex = experiment_factory()
        ex.user = user
        ex.save()
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)

        request = rf.get("/")
        request.user = user
        qs = ob_admin.get_queryset(request)
        assert ob in qs

    def test_get_queryset_superuser(self, ob_admin, outerblock_factory, rf):
        """Verify superusers see all outer block items."""
        superuser = User.objects.create_superuser(
            username="su3", password="pass", email="su3@t.com"
        )
        ob = outerblock_factory()
        request = rf.get("/")
        request.user = superuser
        qs = ob_admin.get_queryset(request)
        assert ob in qs

    def test_get_queryset_public(
        self,
        ob_admin,
        outerblock_factory,
        listitem_factory,
        experiment_factory,
        user,
        rf,
    ):
        """Verify outer blocks from public experiments are visible to non-owners."""
        other_user = User.objects.create_user(username="ob_owner", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "PUB"
        ex.save()
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)

        request = rf.get("/")
        request.user = user
        qs = ob_admin.get_queryset(request)
        assert ob in qs

    def test_get_queryset_private_hidden(
        self,
        ob_admin,
        outerblock_factory,
        listitem_factory,
        experiment_factory,
        user,
        rf,
    ):
        """Verify outer blocks from private experiments are hidden from non-owners."""
        other_user = User.objects.create_user(username="ob_owner2", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "OWN"
        ex.save()
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)

        request = rf.get("/")
        request.user = user
        qs = ob_admin.get_queryset(request)
        assert ob not in qs

    def test_get_queryset_group_shared(
        self,
        ob_admin,
        outerblock_factory,
        listitem_factory,
        experiment_factory,
        user,
        group,
        rf,
    ):
        """Verify outer blocks from group-shared experiments are visible to members."""
        user.groups.add(group)
        other_user = User.objects.create_user(username="ob_grp_owner", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "GRP"
        ex.save()
        ex.sharing_groups.add(group)
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)

        request = rf.get("/")
        request.user = user
        qs = ob_admin.get_queryset(request)
        assert ob in qs


# ---------------------------------------------------------------------------
# BlockItemAdmin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBlockItemAdmin:
    """Tests for BlockItemAdmin queryset filtering and helper methods."""

    @pytest.fixture
    def bi_admin(self, admin_site):
        """Return a BlockItemAdmin instance bound to the test admin site."""
        return BlockItemAdmin(BlockItem, admin_site)

    def test_get_listitem(
        self,
        bi_admin,
        blockitem_factory,
        outerblock_factory,
        listitem_factory,
        experiment_factory,
    ):
        """Verify get_listitem returns the list item for a given block."""
        li = listitem_factory()
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)
        assert bi_admin.get_listitem(bi) == li

    def test_get_experiment(
        self,
        bi_admin,
        blockitem_factory,
        outerblock_factory,
        listitem_factory,
        experiment_factory,
    ):
        """Verify get_experiment returns the experiment for a given block."""
        ex = experiment_factory()
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)
        assert bi_admin.get_experiment(bi) == ex

    def test_get_model_perms_returns_empty(self, bi_admin, rf, user):
        """Verify get_model_perms returns an empty dict to hide the model from menus."""
        request = rf.get("/")
        request.user = user
        assert bi_admin.get_model_perms(request) == {}

    def test_get_queryset_owner(
        self,
        bi_admin,
        blockitem_factory,
        outerblock_factory,
        listitem_factory,
        experiment_factory,
        user,
        rf,
    ):
        """Verify owners see block items from their own experiments."""
        ex = experiment_factory()
        ex.user = user
        ex.save()
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)

        request = rf.get("/")
        request.user = user
        qs = bi_admin.get_queryset(request)
        assert bi in qs

    def test_get_queryset_superuser(self, bi_admin, blockitem_factory, rf):
        """Verify superusers see all block items."""
        superuser = User.objects.create_superuser(
            username="su4", password="pass", email="su4@t.com"
        )
        bi = blockitem_factory()
        request = rf.get("/")
        request.user = superuser
        qs = bi_admin.get_queryset(request)
        assert bi in qs

    def test_get_queryset_public(
        self,
        bi_admin,
        blockitem_factory,
        outerblock_factory,
        listitem_factory,
        experiment_factory,
        user,
        rf,
    ):
        """Verify block items from public experiments are visible to non-owners."""
        other_user = User.objects.create_user(username="bi_owner", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "PUB"
        ex.save()
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)

        request = rf.get("/")
        request.user = user
        qs = bi_admin.get_queryset(request)
        assert bi in qs

    def test_get_queryset_private_hidden(
        self,
        bi_admin,
        blockitem_factory,
        outerblock_factory,
        listitem_factory,
        experiment_factory,
        user,
        rf,
    ):
        """Verify block items from private experiments are hidden from non-owners."""
        other_user = User.objects.create_user(username="bi_owner2", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "OWN"
        ex.save()
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)

        request = rf.get("/")
        request.user = user
        qs = bi_admin.get_queryset(request)
        assert bi not in qs

    def test_get_queryset_group_shared(
        self,
        bi_admin,
        blockitem_factory,
        outerblock_factory,
        listitem_factory,
        experiment_factory,
        user,
        group,
        rf,
    ):
        """Verify block items from group-shared experiments are visible to members."""
        user.groups.add(group)
        other_user = User.objects.create_user(username="bi_grp_owner", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "GRP"
        ex.save()
        ex.sharing_groups.add(group)
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)

        request = rf.get("/")
        request.user = user
        qs = bi_admin.get_queryset(request)
        assert bi in qs


# ---------------------------------------------------------------------------
# SubjectDataAdmin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSubjectDataAdmin:
    """Tests for SubjectDataAdmin queryset filtering and permission methods."""

    def test_get_queryset_owner(
        self, subject_data_admin, subjectdata_factory, experiment_factory, user, rf
    ):
        """Verify owners see subject data records from their own experiments."""
        ex = experiment_factory()
        ex.user = user
        ex.save()
        sd = subjectdata_factory(experiment=ex)

        request = rf.get("/")
        request.user = user
        qs = subject_data_admin.get_queryset(request)
        assert sd in qs

    def test_get_queryset_superuser(
        self, subject_data_admin, subjectdata_factory, experiment_factory, rf
    ):
        """Verify superusers see all subject data records."""
        superuser = User.objects.create_superuser(
            username="su5", password="pass", email="su5@t.com"
        )
        sd = subjectdata_factory()

        request = rf.get("/")
        request.user = superuser
        qs = subject_data_admin.get_queryset(request)
        assert sd in qs

    def test_get_queryset_public(
        self, subject_data_admin, subjectdata_factory, experiment_factory, user, rf
    ):
        """Verify subject data from public experiments is visible to non-owners."""
        other_user = User.objects.create_user(username="sd_owner", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "PUB"
        ex.save()
        sd = subjectdata_factory(experiment=ex)

        request = rf.get("/")
        request.user = user
        qs = subject_data_admin.get_queryset(request)
        assert sd in qs

    def test_get_queryset_private_hidden(
        self, subject_data_admin, subjectdata_factory, experiment_factory, user, rf
    ):
        """Verify subject data from private experiments is hidden from non-owners."""
        other_user = User.objects.create_user(username="sd_owner2", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "OWN"
        ex.save()
        sd = subjectdata_factory(experiment=ex)

        request = rf.get("/")
        request.user = user
        qs = subject_data_admin.get_queryset(request)
        assert sd not in qs

    def test_get_queryset_group_shared(
        self,
        subject_data_admin,
        subjectdata_factory,
        experiment_factory,
        user,
        group,
        rf,
    ):
        """Verify subject data from group-shared experiments is visible to members."""
        user.groups.add(group)
        other_user = User.objects.create_user(username="sd_grp_owner", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "GRP"
        ex.save()
        ex.sharing_groups.add(group)
        sd = subjectdata_factory(experiment=ex)

        request = rf.get("/")
        request.user = user
        qs = subject_data_admin.get_queryset(request)
        assert sd in qs

    def test_has_change_permission_no_obj(self, subject_data_admin, user, rf):
        """Verify has_change_permission returns True when no object is given."""
        request = rf.get("/")
        request.user = user
        assert subject_data_admin.has_change_permission(request) is True

    def test_has_change_permission_owner(
        self, subject_data_admin, subjectdata_factory, experiment_factory, user, rf
    ):
        """Verify the experiment owner has change permission on subject data."""
        ex = experiment_factory()
        ex.user = user
        ex.save()
        sd = subjectdata_factory(experiment=ex)

        request = rf.get("/")
        request.user = user
        assert subject_data_admin.has_change_permission(request, sd) is True

    def test_has_change_permission_non_owner(
        self, subject_data_admin, subjectdata_factory, experiment_factory, user, rf
    ):
        """Verify non-owners lack change permission on private experiment data."""
        ex = experiment_factory()
        ex.sharing_option = "OWN"
        ex.save()
        sd = subjectdata_factory(experiment=ex)

        other_user = User.objects.create_user(username="sd_nonowner", password="pass")
        request = rf.get("/")
        request.user = other_user
        assert subject_data_admin.has_change_permission(request, sd) is False

    def test_has_change_permission_public(
        self, subject_data_admin, subjectdata_factory, experiment_factory, user, rf
    ):
        """Verify anyone has change permission on subject data of public experiment."""
        ex = experiment_factory()
        ex.sharing_option = "PUB"
        ex.save()
        sd = subjectdata_factory(experiment=ex)

        other_user = User.objects.create_user(username="sd_pub_user", password="pass")
        request = rf.get("/")
        request.user = other_user
        assert subject_data_admin.has_change_permission(request, sd) is True

    def test_has_change_permission_group_matching(
        self,
        subject_data_admin,
        subjectdata_factory,
        experiment_factory,
        user,
        group,
        rf,
    ):
        """Verify members have change permission on group-shared experiment data."""
        user.groups.add(group)
        ex = experiment_factory()
        ex.sharing_option = "GRP"
        ex.save()
        ex.sharing_groups.add(group)
        sd = subjectdata_factory(experiment=ex)

        request = rf.get("/")
        request.user = user
        assert subject_data_admin.has_change_permission(request, sd) is True

    def test_has_change_permission_superuser(
        self, subject_data_admin, subjectdata_factory, experiment_factory, rf
    ):
        """Verify superusers always have change permission on any subject data."""
        superuser = User.objects.create_superuser(
            username="su6", password="pass", email="su6@t.com"
        )
        sd = subjectdata_factory()

        request = rf.get("/")
        request.user = superuser
        assert subject_data_admin.has_change_permission(request, sd) is True

    def test_has_add_permission_returns_false(self, subject_data_admin, user, rf):
        """Verify has_add_permission always returns False."""
        request = rf.get("/")
        request.user = user
        assert subject_data_admin.has_add_permission(request) is False

    @pytest.mark.parametrize("is_owner", [False, True], ids=["member", "owner"])
    @pytest.mark.parametrize("sharing_option", ["GRP", "PUB"])
    @pytest.mark.parametrize(
        "exp_groups, user_groups",
        [
            (["A"], ["A"]),
            (["A"], ["A", "B"]),
            (["A", "B"], ["A"]),
            (["A", "B"], ["B"]),
            (["A", "B"], ["A", "B"]),
        ],
        ids=[
            "exp-A_user-A",
            "exp-A_user-AB",
            "exp-AB_user-A",
            "exp-AB_user-B",
            "exp-AB_user-AB",
        ],
    )
    def test_shared_subject_listed_once(
        self,
        subject_data_admin,
        subjectdata_factory,
        experiment_factory,
        user,
        rf,
        exp_groups,
        user_groups,
        sharing_option,
        is_owner,
    ):
        """Verify shared subject data is not duplicated and opens without error."""
        groups = {name: Group.objects.create(name=name) for name in ["A", "B"]}
        user.groups.add(*(groups[name] for name in user_groups))
        ex = experiment_factory()
        if not is_owner:
            ex.user = User.objects.create_user(username="grp_owner", password="pass")
        ex.sharing_option = sharing_option
        ex.save()
        ex.sharing_groups.add(*(groups[name] for name in exp_groups))
        sd = subjectdata_factory(experiment=ex)

        request = rf.get("/")
        request.user = user
        qs = subject_data_admin.get_queryset(request)
        assert qs.filter(pk=sd.pk).count() == 1
        # change view uses get_object; duplicates raise MultipleObjectsReturned (500)
        assert subject_data_admin.get_object(request, str(sd.pk)) == sd


# ---------------------------------------------------------------------------
# TrialResultAdmin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTrialResultAdmin:
    """Tests for TrialResultAdmin queryset filtering and permission methods."""

    @override_settings(WEBCAM_URL="/webcam/")
    def test_webcam_file_link_with_file(self, trial_result_admin):
        """Verify webcam_file_link returns the full webcam URL when a file exists."""
        obj = MagicMock()
        obj.webcam_file = MagicMock()
        obj.filename = "subject/video.webm"
        result = trial_result_admin.webcam_file_link(obj)
        assert result == "/webcam/subject/video.webm"

    def test_webcam_file_link_without_file(self, trial_result_admin):
        """Verify webcam_file_link returns '-' when no webcam file is attached."""
        obj = MagicMock()
        obj.webcam_file = None
        assert trial_result_admin.webcam_file_link(obj) == "-"

    def test_get_form_sets_exclude(self, trial_result_admin, rf, user):
        """Verify get_form sets the webcam_file field in the exclude tuple."""
        request = rf.get("/")
        request.user = user
        with patch.object(admin.ModelAdmin, "get_form", return_value=MagicMock()):
            trial_result_admin.get_form(request)
        assert trial_result_admin.exclude == ("webcam_file",)

    def test_get_model_perms_returns_empty(self, trial_result_admin, rf, user):
        """Verify get_model_perms returns an empty dict to hide the model from menus."""
        request = rf.get("/")
        request.user = user
        assert trial_result_admin.get_model_perms(request) == {}

    def test_has_add_permission_returns_false(self, trial_result_admin, user, rf):
        """Verify has_add_permission always returns False."""
        request = rf.get("/")
        request.user = user
        assert trial_result_admin.has_add_permission(request) is False

    def test_get_queryset_owner(
        self,
        trial_result_admin,
        trialresult_factory,
        subjectdata_factory,
        experiment_factory,
        user,
        rf,
    ):
        """Verify owners see trial results from their own experiments."""
        ex = experiment_factory()
        ex.user = user
        ex.save()
        sd = subjectdata_factory(experiment=ex)
        tr = trialresult_factory(subject=sd)

        request = rf.get("/")
        request.user = user
        qs = trial_result_admin.get_queryset(request)
        assert tr in qs

    def test_get_queryset_superuser(self, trial_result_admin, trialresult_factory, rf):
        """Verify superusers see all trial results."""
        superuser = User.objects.create_superuser(
            username="su7", password="pass", email="su7@t.com"
        )
        tr = trialresult_factory()

        request = rf.get("/")
        request.user = superuser
        qs = trial_result_admin.get_queryset(request)
        assert tr in qs

    def test_get_queryset_public(
        self,
        trial_result_admin,
        trialresult_factory,
        subjectdata_factory,
        experiment_factory,
        user,
        rf,
    ):
        """Verify trial results from public experiments are visible to non-owners."""
        other_user = User.objects.create_user(username="tr_owner", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "PUB"
        ex.save()
        sd = subjectdata_factory(experiment=ex)
        tr = trialresult_factory(subject=sd)

        request = rf.get("/")
        request.user = user
        qs = trial_result_admin.get_queryset(request)
        assert tr in qs

    def test_get_queryset_private_hidden(
        self,
        trial_result_admin,
        trialresult_factory,
        subjectdata_factory,
        experiment_factory,
        user,
        rf,
    ):
        """Verify trial results from private experiments are hidden from non-owners."""
        other_user = User.objects.create_user(username="tr_owner2", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "OWN"
        ex.save()
        sd = subjectdata_factory(experiment=ex)
        tr = trialresult_factory(subject=sd)

        request = rf.get("/")
        request.user = user
        qs = trial_result_admin.get_queryset(request)
        assert tr not in qs

    def test_get_queryset_group_shared(
        self,
        trial_result_admin,
        trialresult_factory,
        subjectdata_factory,
        experiment_factory,
        user,
        group,
        rf,
    ):
        """Verify trial results from group-shared experiments are visible to members."""
        user.groups.add(group)
        other_user = User.objects.create_user(username="tr_grp_owner", password="pass")
        ex = experiment_factory()
        ex.user = other_user
        ex.sharing_option = "GRP"
        ex.save()
        ex.sharing_groups.add(group)
        sd = subjectdata_factory(experiment=ex)
        tr = trialresult_factory(subject=sd)

        request = rf.get("/")
        request.user = user
        qs = trial_result_admin.get_queryset(request)
        assert tr in qs

    def test_has_change_permission_no_obj(self, trial_result_admin, user, rf):
        """Verify has_change_permission returns True when no object is given."""
        request = rf.get("/")
        request.user = user
        assert trial_result_admin.has_change_permission(request) is True

    def test_has_change_permission_owner(
        self,
        trial_result_admin,
        trialresult_factory,
        subjectdata_factory,
        experiment_factory,
        user,
        rf,
    ):
        """Verify the experiment owner has change permission on their trial results."""
        ex = experiment_factory()
        ex.user = user
        ex.save()
        sd = subjectdata_factory(experiment=ex)
        tr = trialresult_factory(subject=sd)

        request = rf.get("/")
        request.user = user
        assert trial_result_admin.has_change_permission(request, tr) is True

    def test_has_change_permission_non_owner(
        self,
        trial_result_admin,
        trialresult_factory,
        subjectdata_factory,
        experiment_factory,
        user,
        rf,
    ):
        """Verify non-owners lack change permission on private experiment results."""
        ex = experiment_factory()
        ex.sharing_option = "OWN"
        ex.save()
        sd = subjectdata_factory(experiment=ex)
        tr = trialresult_factory(subject=sd)

        other_user = User.objects.create_user(username="tr_nonowner", password="pass")
        request = rf.get("/")
        request.user = other_user
        assert trial_result_admin.has_change_permission(request, tr) is False

    def test_has_change_permission_public(
        self,
        trial_result_admin,
        trialresult_factory,
        subjectdata_factory,
        experiment_factory,
        user,
        rf,
    ):
        """Verify anyone has change permission on TrialResults of public experiment."""
        ex = experiment_factory()
        ex.sharing_option = "PUB"
        ex.save()
        sd = subjectdata_factory(experiment=ex)
        tr = trialresult_factory(subject=sd)

        other_user = User.objects.create_user(username="tr_pub_user", password="pass")
        request = rf.get("/")
        request.user = other_user
        assert trial_result_admin.has_change_permission(request, tr) is True

    def test_has_change_permission_group_matching(
        self,
        trial_result_admin,
        trialresult_factory,
        subjectdata_factory,
        experiment_factory,
        user,
        group,
        rf,
    ):
        """Verify group members have change permission on group-shared trial results."""
        user.groups.add(group)
        ex = experiment_factory()
        ex.sharing_option = "GRP"
        ex.save()
        ex.sharing_groups.add(group)
        sd = subjectdata_factory(experiment=ex)
        tr = trialresult_factory(subject=sd)

        request = rf.get("/")
        request.user = user
        assert trial_result_admin.has_change_permission(request, tr) is True

    def test_has_change_permission_superuser(
        self, trial_result_admin, trialresult_factory, rf
    ):
        """Verify superusers always have change permission on any trial result."""
        superuser = User.objects.create_superuser(
            username="su8", password="pass", email="su8@t.com"
        )
        tr = trialresult_factory()

        request = rf.get("/")
        request.user = superuser
        assert trial_result_admin.has_change_permission(request, tr) is True


# ---------------------------------------------------------------------------
# TrialItemInline — attention getter scoping and formset validation
# ---------------------------------------------------------------------------


@pytest.fixture
def ag_block_setup(trialitem_factory, attention_getter_factory, filer_file_factory):
    """Block with trial T1 plus AG (own block, same list) and AG2 (other list)."""
    visual = filer_file_factory("pic.png")
    trial = trialitem_factory(label="T1")
    ag = attention_getter_factory(trial, label="AG", link=False)
    other_ag = trialitem_factory(label="AG2", code="AG2")  # different experiment
    other_ag.trial_type = "AG"
    for t in (trial, ag, other_ag):
        t.visual_file = visual
        t.save()
    exp = trial.blockitem.outerblockitem.listitem.experiment
    exp.recording_option = Experiment.EYE  # dwell fields only exist for eye-tracking
    exp.save()
    return trial, ag, other_ag


def _inline_request(rf, user, block):
    request = rf.get("/")
    user.is_superuser = True  # admin forms ignore edits without change permission
    request.user = user
    request.resolver_match = SimpleNamespace(kwargs={"object_id": str(block.pk)})
    return request


def _attention_getter_field(admin_site, rf, user, trial):
    inline = TrialItemInline(BlockItem, admin_site)
    return inline.formfield_for_foreignkey(
        TrialItem._meta.get_field("attention_getter"),
        _inline_request(rf, user, trial.blockitem),
    )


@pytest.mark.django_db
def test_attention_getter_choices_limited_to_same_list(
    admin_site, rf, user, ag_block_setup
):
    """Only flagged trials from the block's own list are offered."""
    trial, ag, _ = ag_block_setup
    field = _attention_getter_field(admin_site, rf, user, trial)
    assert list(field.queryset) == [ag]


@pytest.mark.django_db
def test_attention_getter_choice_label_shows_full_location(
    admin_site, rf, user, ag_block_setup
):
    """The dropdown label names the trial, its outer block and its block."""
    trial, ag, _ = ag_block_setup
    field = _attention_getter_field(admin_site, rf, user, trial)
    block = ag.blockitem
    expected = f"AG — {block.outerblockitem.outer_block_name} › {block.label}"  # noqa: RUF001
    assert field.label_from_instance(ag) == expected


@pytest.mark.django_db
def test_attention_getter_help_text_explains_scope(
    admin_site, rf, user, ag_block_setup
):
    """The help text states which trials are listed."""
    trial, _, _ = ag_block_setup
    field = _attention_getter_field(admin_site, rf, user, trial)
    assert field.help_text.endswith(
        " Lists every trial marked as an attention getter in this list, from any block."
    )


def _formset_data(trials, overrides):
    """POST data for the trial inline formset; overrides: {pk: {field: value|None}}."""
    prefix = "trialitem_set"
    data = {
        f"{prefix}-TOTAL_FORMS": str(len(trials)),
        f"{prefix}-INITIAL_FORMS": str(len(trials)),
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }
    for i, t in enumerate(trials):
        values = {
            "id": t.pk,
            "blockitem": t.blockitem_id,
            "label": t.label,
            "code": t.code,
            "visual_onset": 0,
            "visual_file": t.visual_file_id,
            "audio_onset": 0,
            "user_input": "NO",
            "max_duration": 1000,
            "record_media": "on",
            "record_gaze": "on",
            "calibration_points": json.dumps(t.calibration_points),
            "grid_row": 1,
            "grid_col": 1,
            "position": t.position,
            "dwell_target_type": "ANY",
        }
        values["trial_type"] = t.trial_type
        values.update(overrides.get(t.pk, {}))
        data.update(
            {f"{prefix}-{i}-{k}": v for k, v in values.items() if v is not None}
        )
    return data


@pytest.mark.django_db
def test_formset_rejects_pointing_at_attention_getter_unflagged_in_same_save(
    admin_site, rf, user, ag_block_setup
):
    """Unflagging AG and pointing T1 at it in one save is caught by the formset."""
    trial, ag, _ = ag_block_setup
    ag.blockitem = trial.blockitem  # same block → same formset
    ag.position = 2
    ag.save()
    inline = TrialItemInline(BlockItem, admin_site)
    request = _inline_request(rf, user, trial.blockitem)
    formset_cls = inline.get_formset(request, trial.blockitem)
    data = _formset_data(
        [trial, ag],
        {
            trial.pk: {"attention_getter": ag.pk, "min_dwell_time": 500},
            ag.pk: {"trial_type": "REG"},
        },
    )
    formset = formset_cls(data, instance=trial.blockitem, prefix="trialitem_set")
    assert not formset.is_valid()
    assert "being changed from an attention getter" in str(formset.errors)


@pytest.mark.django_db
def test_formset_accepts_valid_dwell_check(admin_site, rf, user, ag_block_setup):
    """A valid dwell-check configuration saves through the inline formset."""
    trial, ag, _ = ag_block_setup
    inline = TrialItemInline(BlockItem, admin_site)
    request = _inline_request(rf, user, trial.blockitem)
    formset_cls = inline.get_formset(request, trial.blockitem)
    data = _formset_data(
        [trial], {trial.pk: {"attention_getter": ag.pk, "min_dwell_time": 500}}
    )
    formset = formset_cls(data, instance=trial.blockitem, prefix="trialitem_set")
    assert formset.is_valid(), formset.errors
    formset.save()
    trial.refresh_from_db()
    assert trial.attention_getter == ag


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("model", "get_obj"),
    [
        pytest.param(
            "experiment",
            lambda t: t.blockitem.outerblockitem.listitem.experiment,
            id="experiment",
        ),
        pytest.param(
            "listitem", lambda t: t.blockitem.outerblockitem.listitem, id="listitem"
        ),
        pytest.param("blockitem", lambda t: t.blockitem, id="blockitem"),
    ],
)
def test_delete_confirmation_with_attention_getter_is_not_blocked(
    client, trialitem_factory, attention_getter_factory, model, get_obj
):
    """Deleting a parent holding a trigger and its attention getter can be confirmed."""
    trial = trialitem_factory()
    ag = attention_getter_factory(trial)
    ag.blockitem = trial.blockitem  # same block, so the blockitem case holds both
    ag.save()
    client.force_login(User.objects.create_superuser("deladmin", "d@x.org", "pw"))
    url = reverse(f"admin:experiments_{model}_delete", args=[get_obj(trial).pk])
    response = client.get(url)
    assert response.status_code == 200
    assert b"Cannot delete" not in response.content
    client.post(url, {"post": "yes"})
    assert not TrialItem.objects.filter(pk__in=[trial.pk, ag.pk]).exists()


@pytest.mark.django_db
def test_inline_delete_of_referenced_attention_getter_gives_form_error(
    admin_site, rf, user, trialitem_factory, attention_getter_factory
):
    """Ticking DELETE on an attention getter still in use is a form error, not a 500."""
    trial = trialitem_factory()
    ag = attention_getter_factory(trial)
    inline = TrialItemInline(BlockItem, admin_site)
    request = _inline_request(rf, user, ag.blockitem)
    formset_cls = inline.get_formset(request, ag.blockitem)
    data = _formset_data([ag], {ag.pk: {"DELETE": "on"}})
    formset = formset_cls(data, instance=ag.blockitem, prefix="trialitem_set")
    assert not formset.is_valid()
    assert "would require deleting" in str(formset.non_form_errors())


@pytest.mark.django_db
def test_listitem_change_view_renders_flowchart(client, listitem_factory):
    """The list change page includes the Mermaid flowchart source."""
    listitem = listitem_factory()
    admin_user = User.objects.create_superuser("flowadmin", "f@x.org", "pw")
    client.force_login(admin_user)
    url = reverse("admin:experiments_listitem_change", args=[listitem.pk])
    response = client.get(url)
    assert response.status_code == 200
    assert b'class="mermaid"' in response.content
    assert b"flowchart TD" in response.content
    # Same group markup as the neighbouring inline sections, with open/close icons
    assert b'class="inline-group grp-group grp-stacked" id="flowchart-group"' in (
        response.content
    )
    assert b'class="grp-icon grp-close-handler" title="Close"' in response.content


# ---------------------------------------------------------------------------
# TrialItemInline — layout and eye-tracking visibility
# ---------------------------------------------------------------------------


@pytest.fixture
def block_page(client, trialitem_factory):
    """Return (trial, fetch) where fetch(recording_option) renders the block page."""
    trial = trialitem_factory()
    client.force_login(User.objects.create_superuser("layoutadmin", "l@x.org", "pw"))

    def fetch(recording_option):
        exp = trial.blockitem.outerblockitem.listitem.experiment
        exp.recording_option = recording_option
        exp.save()
        url = reverse("admin:experiments_blockitem_change", args=[trial.blockitem.pk])
        response = client.get(url)
        assert response.status_code == 200
        return response.content.decode()

    fetch.trial = trial
    return fetch


@pytest.mark.django_db
@pytest.mark.parametrize(
    "option",
    [pytest.param(Experiment.EYE, id="eye"), pytest.param(Experiment.ALL, id="all")],
)
def test_trial_inline_sections_in_order_without_collapse(block_page, option):
    """Eye-tracking experiments show every section, in order, none collapsible."""
    html = block_page(option)
    titles = [
        "Stimulus",
        "Response",
        "Recording",
        "Grid",
        "Eye-tracking calibration",
        "Gaze dwell time check",
    ]
    found = [
        re.search(rf'<fieldset class="([^"]*)"><h4[^>]*>{t}</h4>', html) for t in titles
    ]
    assert all(found)
    positions = [m.start() for m in found]
    assert positions == sorted(positions)
    assert 'name="trialitem_set-0-trial_type"' in html
    assert all("grp-collapse" not in m.group(1) for m in found)
    assert "eye-calibration" in found[4].group(1)
    assert "dwell-check" in found[5].group(1)


@pytest.mark.django_db
@pytest.mark.parametrize("label", ["Visual file", "Audio file", "Attention getter"])
def test_trial_inline_labels_have_no_colon(block_page, label):
    """File and FK labels render without a trailing colon."""
    html = block_page(Experiment.EYE)
    assert f">{label}:<" not in html
    assert f">{label}<" in html


@pytest.mark.django_db
@pytest.mark.parametrize(
    "option",
    [
        pytest.param(Experiment.NONE, id="key-click-only"),
        pytest.param(Experiment.AUDIO, id="audio"),
        pytest.param(Experiment.VIDEO, id="video"),
    ],
)
def test_trial_inline_hides_eye_tracking_for_other_recording_options(
    block_page, option
):
    """Without eye-tracking, its sections and fields are not rendered."""
    html = block_page(option)
    assert "Eye-tracking calibration" not in html
    assert "Gaze dwell time check" not in html
    assert "record_gaze" not in html
    assert "trial_type" not in html
    assert ">Recording</h4>" in html


def test_trial_inline_add_page_shows_all_fieldsets(admin_site, rf, user):
    """With no parent block (add page) every fieldset, eye-tracking included, shows."""
    request = rf.get("/")
    request.user = user
    fieldsets = TrialItemInline(BlockItem, admin_site).get_fieldsets(request, None)
    names = [name for name, _ in fieldsets]
    fields = [f for _, opts in fieldsets for f in opts["fields"]]
    assert "Gaze dwell time check" in names
    assert "Eye-tracking calibration" in names
    assert "trial_type" in fields


@pytest.mark.django_db
def test_non_eye_save_keeps_trial_type_and_dwell_values(
    admin_site,
    rf,
    user,
    trialitem_factory,
    attention_getter_factory,
    filer_file_factory,
):
    """Fields hidden from the form keep their saved values on save."""
    trial = trialitem_factory(label="T1")
    ag = attention_getter_factory(trial, link=True)
    trial.trial_type = TrialItem.REGULAR
    trial.dwell_target_type = "CELL"
    trial.dwell_target_row = 1
    trial.dwell_target_col = 2
    trial.grid_col = 2
    trial.record_gaze = True
    trial.visual_file = filer_file_factory("pic.png")
    trial.save()
    exp = trial.blockitem.outerblockitem.listitem.experiment
    exp.recording_option = Experiment.NONE
    exp.save()
    inline = TrialItemInline(BlockItem, admin_site)
    request = _inline_request(rf, user, trial.blockitem)
    data = _formset_data([trial], {trial.pk: {"grid_col": 2}})
    formset = inline.get_formset(request, trial.blockitem)(
        data, instance=trial.blockitem, prefix="trialitem_set"
    )
    assert "trial_type" not in formset.forms[0].fields
    assert formset.is_valid(), formset.errors
    formset.save()
    trial.refresh_from_db()
    assert trial.trial_type == TrialItem.REGULAR
    assert trial.attention_getter == ag
    assert (trial.dwell_target_type, trial.dwell_target_row) == ("CELL", 1)


@pytest.mark.django_db
def test_non_eye_hidden_field_error_becomes_non_field_error(
    admin_site,
    rf,
    user,
    trialitem_factory,
    attention_getter_factory,
    filer_file_factory,
):
    """An error on a hidden eye-tracking field is shown with a hint, not a 500."""
    trial = trialitem_factory(label="T1")
    attention_getter_factory(trial, link=True)
    trial.dwell_target_type, trial.dwell_target_row, trial.dwell_target_col = (
        "CELL",
        2,
        1,
    )
    trial.grid_row = 2
    trial.record_gaze = True
    trial.visual_file = filer_file_factory("pic.png")
    trial.save()
    exp = trial.blockitem.outerblockitem.listitem.experiment
    exp.recording_option = Experiment.NONE
    exp.save()
    inline = TrialItemInline(BlockItem, admin_site)
    request = _inline_request(rf, user, trial.blockitem)
    data = _formset_data([trial], {trial.pk: {"grid_row": 1, "grid_col": 1}})
    formset = inline.get_formset(request, trial.blockitem)(
        data, instance=trial.blockitem, prefix="trialitem_set"
    )
    assert not formset.is_valid()
    errors = " ".join(formset.forms[0].non_field_errors())
    assert "Gaze dwell time check:" in errors
    assert (
        "set the experiment's Recording option (General Settings) to include"
        " eye-tracking." in errors
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("option", "errors", "expected", "unexpected"),
    [
        pytest.param(
            Experiment.EYE,
            {NON_FIELD_ERRORS: ["Constraint broken."]},
            ["Constraint broken."],
            ["Gaze dwell time check", "Recording option"],
            id="genuine-non-field-error-untouched",
        ),
        pytest.param(
            Experiment.NONE,
            {NON_FIELD_ERRORS: ["Constraint broken."], "trial_type": ["Bad type."]},
            ["Constraint broken.", "Trial type: Bad type. To edit these settings"],
            ["Gaze dwell time check"],
            id="hidden-trial-type-labelled",
        ),
    ],
)
def test_hidden_field_error_labels(
    admin_site, rf, user, ag_block_setup, option, errors, expected, unexpected
):
    """Only errors on hidden fields are relabelled; genuine ones are kept as is."""
    trial, _, _ = ag_block_setup
    exp = trial.blockitem.outerblockitem.listitem.experiment
    exp.recording_option = option
    exp.save()
    inline = TrialItemInline(BlockItem, admin_site)
    request = _inline_request(rf, user, trial.blockitem)
    formset = inline.get_formset(request, trial.blockitem)(
        _formset_data([trial], {}), instance=trial.blockitem, prefix="trialitem_set"
    )
    assert formset.is_valid(), formset.errors
    form = formset.forms[0]
    form._update_errors(ValidationError(errors))
    text = " ".join(form.non_field_errors())
    assert all(e in text for e in expected)
    assert not any(u in text for u in unexpected)


@pytest.mark.django_db
def test_formset_shows_min_dwell_above_max_duration_on_the_field(
    admin_site, rf, user, ag_block_setup
):
    """The max-duration check surfaces as an error on the min_dwell_time field."""
    trial, ag, _ = ag_block_setup
    inline = TrialItemInline(BlockItem, admin_site)
    request = _inline_request(rf, user, trial.blockitem)
    data = _formset_data(
        [trial], {trial.pk: {"attention_getter": ag.pk, "min_dwell_time": 1001}}
    )
    formset = inline.get_formset(request, trial.blockitem)(
        data, instance=trial.blockitem, prefix="trialitem_set"
    )
    assert not formset.is_valid()
    assert "Must not exceed the maximum" in str(
        formset.forms[0].errors["min_dwell_time"]
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("trial_type", "kept"),
    [
        pytest.param("AG", False, id="to-attention-getter-clears"),
        pytest.param("CAL", False, id="to-calibration-clears"),
        pytest.param("REG", True, id="regular-keeps"),
    ],
)
def test_formset_clears_dwell_values_unless_regular(
    admin_site, rf, user, ag_block_setup, trial_type, kept
):
    """Posted dwell values are cleared on save for non-regular trials."""
    trial, ag, _ = ag_block_setup
    inline = TrialItemInline(BlockItem, admin_site)
    request = _inline_request(rf, user, trial.blockitem)
    data = _formset_data(
        [trial],
        {
            trial.pk: {
                "trial_type": trial_type,
                "attention_getter": ag.pk,
                "min_dwell_time": 500,
                "dwell_target_type": "CELL",
                "dwell_target_row": 1,
                "dwell_target_col": 2,
                "grid_col": 2,
            }
        },
    )
    formset = inline.get_formset(request, trial.blockitem)(
        data, instance=trial.blockitem, prefix="trialitem_set"
    )
    assert formset.is_valid(), formset.errors
    formset.save()
    trial.refresh_from_db()
    values = (
        trial.attention_getter,
        trial.min_dwell_time,
        trial.dwell_target_type,
        trial.dwell_target_row,
        trial.dwell_target_col,
    )
    assert values == (
        (ag, 500, "CELL", 1, 2) if kept else (None, None, "ANY", None, None)
    )


# ---------------------------------------------------------------------------
# ExperimentAdmin: turning off eye-tracking
# ---------------------------------------------------------------------------


@pytest.fixture
def eye_setup(
    experiment_factory,
    listitem_factory,
    outerblock_factory,
    blockitem_factory,
    trialitem_factory,
    attention_getter_factory,
):
    """Return a builder of an eye-tracking experiment with a dwell check, AG and CAL."""

    def build(name):
        exp = experiment_factory(exp_name=name)
        exp.recording_option = Experiment.EYE
        exp.save()
        outer = outerblock_factory(listitem=listitem_factory(experiment=exp))
        block = blockitem_factory(outerblock=outer)
        trial = trialitem_factory(blockitem=block, label="T", code="T")
        ag = attention_getter_factory(trial)
        cal = trialitem_factory(blockitem=block, label="C", code="C", position=2)
        cal.trial_type = TrialItem.CALIBRATION
        cal.save()
        return exp, trial, ag, cal

    return build


@pytest.mark.django_db
class TestRecordingOptionChange:
    """Turning off eye-tracking clears dwell checks and resets trial types."""

    @pytest.mark.parametrize(
        ("start", "end", "cleared"),
        [
            pytest.param(Experiment.EYE, Experiment.NONE, True, id="eye-to-none"),
            pytest.param(Experiment.ALL, Experiment.AUDIO, True, id="all-to-audio"),
            pytest.param(Experiment.EYE, Experiment.ALL, False, id="eye-to-all"),
            pytest.param(Experiment.NONE, Experiment.EYE, False, id="none-to-eye"),
            pytest.param(
                Experiment.AUDIO, Experiment.VIDEO, False, id="audio-to-video"
            ),
        ],
    )
    def test_transitions(
        self, experiment_admin, rf, user, eye_setup, start, end, cleared
    ):
        """Only eye to non-eye clears; other transitions leave trials alone."""
        exp, trial, ag, cal = eye_setup("A")
        _, other_trial, other_ag, other_cal = eye_setup("B")
        Experiment.objects.filter(pk=exp.pk).update(recording_option=start)
        exp.recording_option = end
        request = rf.get("/")
        request.user = user
        request._messages = MagicMock()

        experiment_admin.save_model(request, exp, None, True)

        for t in (trial, ag, cal, other_trial, other_ag, other_cal):
            t.refresh_from_db()
        if cleared:
            assert (trial.attention_getter, trial.min_dwell_time) == (None, None)
            assert ag.trial_type == cal.trial_type == TrialItem.REGULAR
            assert request._messages.add.call_args.args[1] == (
                "Recording option no longer includes eye-tracking: cleared gaze dwell "
                "time checks on 1 trial and reset 1 attention getter and 1 "
                "calibration trial to Regular."
            )
        else:
            assert trial.attention_getter == ag
            assert trial.min_dwell_time == 500
            assert ag.trial_type == TrialItem.ATTENTION_GETTER
            assert cal.trial_type == TrialItem.CALIBRATION
            request._messages.add.assert_not_called()
        # the other experiment is untouched
        assert other_trial.attention_getter == other_ag
        assert other_ag.trial_type == TrialItem.ATTENTION_GETTER
        assert other_cal.trial_type == TrialItem.CALIBRATION

    def test_create_does_nothing(self, experiment_admin, rf, user):
        """A new experiment never triggers the cleanup."""
        request = rf.get("/")
        request.user = user
        request._messages = MagicMock()
        exp = Experiment(exp_name="New", recording_option=Experiment.NONE)
        experiment_admin.save_model(request, exp, None, False)
        request._messages.add.assert_not_called()

    def test_change_page_renders_counts(self, client, eye_setup):
        """The change page carries the initial option and counts for the script."""
        exp, *_ = eye_setup("A")
        client.force_login(User.objects.create_superuser("root", "r@x.org", "pw"))
        html = client.get(
            reverse("admin:experiments_experiment_change", args=[exp.pk])
        ).content.decode()
        for attr in (
            'data-initial="EYE"',
            'data-dwell-count="1"',
            'data-attention-getter-count="1"',
            'data-calibration-count="1"',
            "recording-option-confirm.js",
        ):
            assert attr in html


@pytest.mark.parametrize(
    ("counts", "text"),
    [
        pytest.param(
            (1, 4, 1),
            "cleared gaze dwell time checks on 1 trial and reset 4 attention "
            "getters and 1 calibration trial to Regular",
            id="singulars",
        ),
        pytest.param(
            (3, 2, 0),
            "cleared gaze dwell time checks on 3 trials and reset 2 attention "
            "getters to Regular",
            id="no-calibration",
        ),
        pytest.param(
            (0, 0, 2), "reset 2 calibration trials to Regular", id="only-calibration"
        ),
        pytest.param((0, 0, 0), "", id="nothing"),
    ],
)
def test_eye_off_text(counts, text):
    """Plurals are correct and zero parts are omitted."""
    assert eye_off_text(*counts, past=True) == text
