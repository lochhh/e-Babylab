import uuid
import pytest
from django.contrib.auth.models import User, Group
from django.core.files.base import ContentFile
from django.utils import timezone
from filer.models.filemodels import File as FilerFile

from experiments import models as exp_models


def _make_filer_file(filename):
    """Create a minimal filer File object for use in tests that don't read file content."""
    f = FilerFile(original_filename=filename)
    f.file.save(filename, ContentFile(b""), save=True)
    return f


@pytest.fixture
def user(db):
    """Create a basic user for experiments that require a user."""
    return User.objects.create_user(username="testuser", password="pass")


@pytest.fixture
def group(db):
    return Group.objects.create(name="testgroup")


@pytest.fixture
def instrument_factory(db):
    """Create simple Instrument instances with placeholder filer File objects."""
    def _create(instr_name="instr1"):
        return exp_models.Instrument.objects.create(
            instr_name=instr_name,
            words_list=_make_filer_file("words.csv"),
            irt_params=_make_filer_file("irt.csv"),
            f_lm_np_mean=_make_filer_file("f_np_mean.csv"),
            f_lm_np_sd=_make_filer_file("f_np_sd.csv"),
            f_lm_p_mean=_make_filer_file("f_p_mean.csv"),
            f_lm_p_sd=_make_filer_file("f_p_sd.csv"),
            f_bmin=_make_filer_file("f_bmin.csv"),
            f_slope=_make_filer_file("f_slope.csv"),
            m_lm_np_mean=_make_filer_file("m_np_mean.csv"),
            m_lm_np_sd=_make_filer_file("m_np_sd.csv"),
            m_lm_p_mean=_make_filer_file("m_p_mean.csv"),
            m_lm_p_sd=_make_filer_file("m_p_sd.csv"),
            m_bmin=_make_filer_file("m_bmin.csv"),
            m_slope=_make_filer_file("m_slope.csv"),
        )
    return _create


@pytest.fixture
def experiment_factory(db, user):
    """
    Minimal experiment factory; many fields have defaults in the model.
    Usage: experiment_factory(exp_name='My exp')
    """
    def _create(exp_name="Test Experiment"):
        return exp_models.Experiment.objects.create(user=user, exp_name=exp_name)
    return _create


@pytest.fixture
def listitem_factory(db, experiment_factory):
    def _create(list_name="L1", experiment=None, exclude_list=False):
        if experiment is None:
            experiment = experiment_factory()
        return exp_models.ListItem.objects.create(experiment=experiment, list_name=list_name, exclude_list=exclude_list)
    return _create


@pytest.fixture
def outerblock_factory(db, listitem_factory):
    def _create(listitem=None, outer_block_name="Outer", position=1):
        if listitem is None:
            listitem = listitem_factory()
        return exp_models.OuterBlockItem.objects.create(listitem=listitem, outer_block_name=outer_block_name, position=position)
    return _create


@pytest.fixture
def blockitem_factory(db, outerblock_factory):
    def _create(outerblock=None, label="Block", position=1):
        if outerblock is None:
            outerblock = outerblock_factory()
        return exp_models.BlockItem.objects.create(outerblockitem=outerblock, label=label, position=position)
    return _create


@pytest.fixture
def trialitem_factory(db, blockitem_factory):
    def _create(blockitem=None, label="Trial", code="C1", position=1):
        if blockitem is None:
            blockitem = blockitem_factory()
        return exp_models.TrialItem.objects.create(
            blockitem=blockitem, label=label, code=code, max_duration=1000, position=position
        )
    return _create


@pytest.fixture
def subjectdata_factory(db, experiment_factory, listitem_factory):
    def _create(id=None, experiment=None, listitem=None, participant_id=1):
        if experiment is None:
            experiment = experiment_factory()
        if listitem is None:
            listitem = listitem_factory(experiment=experiment)
        if id is None:
            id = str(uuid.uuid4())
        return exp_models.SubjectData.objects.create(id=id, participant_id=participant_id, experiment=experiment, listitem=listitem)
    return _create


@pytest.fixture
def trialresult_factory(db, subjectdata_factory, trialitem_factory):
    def _create(subject=None, trialitem=None, webcam_name=None):
        if subject is None:
            subject = subjectdata_factory()
        if trialitem is None:
            trialitem = trialitem_factory()
        tr = exp_models.TrialResult.objects.create(subject=subject, trialitem=trialitem)
        if webcam_name:
            # assign a file-like name to test filename property / delete behaviour
            tr.webcam_file.name = webcam_name
            tr.save(update_fields=["webcam_file"])
        return tr
    return _create


@pytest.fixture
def question_factory(db, experiment_factory):
    def _create(text="Q", required=False, experiment=None, question_type=exp_models.Question.TEXT, choices="", position=1):
        if experiment is None:
            experiment = experiment_factory()
        return exp_models.Question.objects.create(text=text, required=required, experiment=experiment, question_type=question_type, choices=choices, position=position)
    return _create


@pytest.fixture
def consent_question_factory(db, experiment_factory):
    def _create(text="Consent?", experiment=None, position=1):
        if experiment is None:
            experiment = experiment_factory()
        return exp_models.ConsentQuestion.objects.create(text=text, experiment=experiment, position=position)
    return _create