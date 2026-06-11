"""Unit tests for experiments/admin.py."""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, User
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
    TrialResultAdmin,
    TrialResultInline,
)
from experiments.models import (
    BlockItem,
    Experiment,
    Instrument,
    ListItem,
    OuterBlockItem,
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

    def test_export_to_json(
        self,
        experiment_factory,
        listitem_factory,
        outerblock_factory,
        blockitem_factory,
        trialitem_factory,
    ):
        """Verify exportToJSON returns all expected top-level keys with correct PKs."""
        ex = experiment_factory()
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)
        ti = trialitem_factory(blockitem=bi)

        data = ExperimentAdmin.exportToJSON(ex.id)

        assert "experiment" in data
        assert "lists" in data
        assert "outerblocks" in data
        assert "innerblocks" in data
        assert "trials" in data
        assert "questions" in data
        assert "consentquestions" in data

        assert data["experiment"][0]["pk"] == str(ex.id)
        assert data["trials"][0]["pk"] == ti.id

    def test_export_to_json_includes_questions(
        self, experiment_factory, question_factory, consent_question_factory
    ):
        """Verify exportToJSON separates questions into their keys."""
        ex = experiment_factory()
        question_factory(experiment=ex, text="Q1")
        consent_question_factory(experiment=ex, text="Consent?")

        data = ExperimentAdmin.exportToJSON(ex.id)
        assert len(data["questions"]) == 1
        assert len(data["consentquestions"]) == 1

    def test_import_from_json_creates_new_experiment(
        self, experiment_factory, user, rf
    ):
        """Verify importFromJSON creates a new experiment owned by the request user."""
        ex = experiment_factory()
        data = ExperimentAdmin.exportToJSON(ex.id)
        json_bytes = json.dumps(data).encode("utf-8")

        new_user = User.objects.create_user(username="importer", password="pass")
        request = rf.post("/")
        request.user = new_user

        initial_count = Experiment.objects.count()
        before = timezone.now()
        ExperimentAdmin.importFromJSON(request, json_bytes)
        after = timezone.now()

        assert Experiment.objects.count() == initial_count + 1
        new_exp = Experiment.objects.exclude(pk=ex.pk).first()
        assert new_exp.user == new_user
        assert before <= new_exp.created_on <= after

    def test_import_from_json_with_list_and_structure(
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
        """Verify importFromJSON recreates the full experiment hierarchy."""
        ex = experiment_factory()
        li = listitem_factory(experiment=ex)
        ob = outerblock_factory(listitem=li)
        bi = blockitem_factory(outerblock=ob)
        trialitem_factory(blockitem=bi)
        question_factory(experiment=ex)
        consent_question_factory(experiment=ex)

        data = ExperimentAdmin.exportToJSON(ex.id)
        json_bytes = json.dumps(data).encode("utf-8")

        request = rf.post("/")
        request.user = user

        ExperimentAdmin.importFromJSON(request, json_bytes)

        assert Experiment.objects.count() == 2
        assert ListItem.objects.count() == 2
        assert OuterBlockItem.objects.count() == 2
        assert BlockItem.objects.count() == 2
        assert TrialItem.objects.count() == 2


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
