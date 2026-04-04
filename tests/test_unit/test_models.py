"""Unit tests that cover models.py behaviour and helpers.

These tests exercise:
- experiment_folder, visual_folder, audio_folder helper functions
- model __str__ methods for all models
- OuterBlockItem, BlockItem, TrialItem, ConsentQuestion ordering
- Question.get_choices, validate_list, validate_range, and clean()
- Experiment helper methods that are model-level (subject_questions, consent_questions, get_list_item)
- TrialResult filename property and _delete_file/delete_file receiver behavior
"""

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError

from experiments import models as exp_models

# ---------------------------------------------------------------------------
# Folder helper functions
# ---------------------------------------------------------------------------


def test_experiment_folder():
    """experiment_folder returns the expected upload path."""

    class FakeInstance:
        exp_name = "MyExp"

    result = exp_models.experiment_folder(FakeInstance(), "logo.png")
    assert result == "uploads/experiments/MyExp/logo.png"


def test_visual_folder():
    """visual_folder returns the expected upload path."""

    class FakeExperiment:
        exp_name = "MyExp"

    class FakeListItem:
        experiment = FakeExperiment()
        list_name = "ListA"

    class FakeBlockItem:
        listitem = FakeListItem()

    class FakeInstance:
        blockitem = FakeBlockItem()

    result = exp_models.visual_folder(FakeInstance(), "img.png")
    assert result == "uploads/MyExp/ListA/visual/img.png"


def test_audio_folder():
    """audio_folder returns the expected upload path."""

    class FakeExperiment:
        exp_name = "MyExp"

    class FakeListItem:
        experiment = FakeExperiment()
        list_name = "ListA"

    class FakeBlockItem:
        listitem = FakeListItem()

    class FakeInstance:
        blockitem = FakeBlockItem()

    result = exp_models.audio_folder(FakeInstance(), "sound.mp3")
    assert result == "uploads/MyExp/ListA/audio/sound.mp3"


# ---------------------------------------------------------------------------
# __str__ methods
# ---------------------------------------------------------------------------


def test_instrument_str(instrument_factory):
    inst = instrument_factory(instr_name="My Instrument")
    assert str(inst) == "My Instrument"


def test_experiment_str_and_subject_consent_questions(
    experiment_factory, question_factory, consent_question_factory
):
    ex = experiment_factory(exp_name="ExpName")
    q = question_factory(text="Q1", experiment=ex, position=1)
    cq = consent_question_factory(text="Agree", experiment=ex, position=1)
    assert str(ex) == "ExpName"
    # subject_questions and consent_questions should return QuerySets with our created objects
    assert q in list(ex.subject_questions())
    assert cq in list(ex.consent_questions())


def test_listitem_outerblock_blockitem_str(
    listitem_factory, outerblock_factory, blockitem_factory
):
    li = listitem_factory(list_name="MyList")
    assert str(li) == "MyList"
    ob = outerblock_factory(listitem=li, outer_block_name="O1", position=1)
    bi = blockitem_factory(outerblock=ob, label="B1", position=1)
    assert str(ob) == "O1"
    assert str(bi) == "B1"


def test_trialitem_and_trialresult_and_filename(trialitem_factory, trialresult_factory):
    ti = trialitem_factory(label="T1")
    tr = trialresult_factory(
        trialitem=ti, webcam_name="uploads/exp/list/visual/cam.png"
    )
    assert str(ti) == "T1"
    assert tr.filename == "cam.png"


def test__delete_file_and_delete_file_signal(
    monkeypatch, trialresult_factory, tmp_path
):
    from experiments.models import _delete_file, delete_file

    dummy_path = "/tmp/somefile.to.delete"
    removed = {"ok": False}

    monkeypatch.setattr("os.path.isfile", lambda p: True if p == dummy_path else False)

    def fake_remove(p):
        removed["ok"] = True

    monkeypatch.setattr("os.remove", fake_remove)

    _delete_file(dummy_path)
    assert removed["ok"] is True

    # test delete_file: create a TrialResult-like object with webcam_file.name
    class Dummy:
        def __init__(self, name):
            self.webcam_file = type("X", (), {"name": name})

    monkeypatch.setattr(settings, "WEBCAM_ROOT", "/tmp", raising=False)
    monkeypatch.setattr("os.path.isfile", lambda p: True)
    removed["ok"] = False
    monkeypatch.setattr("os.remove", fake_remove)
    inst = Dummy("videofile.mp4")
    # import and call delete_file (signature: sender, instance, *args, **kwargs)
    delete_file(None, inst)
    assert removed["ok"] is True


def test_question_get_choices_and_validation(question_factory):
    q = question_factory(text="What?", choices="a, b, c")
    assert q.get_choices() == (("a", "a"), ("b", "b"), ("c", "c"))
    # validate_list
    with pytest.raises(ValidationError):
        exp_models.validate_list("single")
    exp_models.validate_list("a,b")
    # validate_range
    with pytest.raises(ValidationError):
        exp_models.validate_range("x,y")
    with pytest.raises(ValidationError):
        exp_models.validate_range("1,2,3")
    with pytest.raises(ValidationError):
        exp_models.validate_range("5,1")
    # clean() enforces list/range rules for type-specific questions
    q_radio = question_factory(question_type=exp_models.Question.RADIO, choices="")
    with pytest.raises(ValidationError):
        q_radio.clean()
    q_range = question_factory(
        question_type=exp_models.Question.NUM_RANGE, choices="1, 10"
    )
    # should not raise
    q_range.clean()


def test_subjectdata_question_consentquestion_str(
    subjectdata_factory, question_factory, consent_question_factory
):
    """__str__ returns expected strings for SubjectData, Question, ConsentQuestion."""
    sd = subjectdata_factory()
    assert str(sd) == sd.id

    q = question_factory(text="How old are you?")
    assert str(q) == "How old are you?"

    cq = consent_question_factory(text="Do you agree?")
    assert str(cq) == "Do you agree?"


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_outerblockitem_ordering(listitem_factory, outerblock_factory):
    """OuterBlockItem queryset is ordered by position ascending."""
    li = listitem_factory()
    outerblock_factory(listitem=li, outer_block_name="Second", position=2)
    outerblock_factory(listitem=li, outer_block_name="First", position=1)
    names = list(
        exp_models.OuterBlockItem.objects.filter(listitem=li).values_list(
            "outer_block_name", flat=True
        )
    )
    assert names == ["First", "Second"]


def test_blockitem_ordering(outerblock_factory, blockitem_factory):
    """BlockItem queryset is ordered by position ascending."""
    ob = outerblock_factory()
    blockitem_factory(outerblock=ob, label="B2", position=2)
    blockitem_factory(outerblock=ob, label="B1", position=1)
    labels = list(
        exp_models.BlockItem.objects.filter(outerblockitem=ob).values_list(
            "label", flat=True
        )
    )
    assert labels == ["B1", "B2"]


def test_trialitem_ordering(blockitem_factory, trialitem_factory):
    """TrialItem queryset is ordered by position ascending."""
    bi = blockitem_factory()
    trialitem_factory(blockitem=bi, label="T2", code="C2", position=2)
    trialitem_factory(blockitem=bi, label="T1", code="C1", position=1)
    labels = list(
        exp_models.TrialItem.objects.filter(blockitem=bi).values_list(
            "label", flat=True
        )
    )
    assert labels == ["T1", "T2"]


def test_consentquestion_ordering(experiment_factory, consent_question_factory):
    """ConsentQuestion queryset is ordered by position ascending."""
    ex = experiment_factory()
    consent_question_factory(text="Second", experiment=ex, position=2)
    consent_question_factory(text="First", experiment=ex, position=1)
    texts = list(
        exp_models.ConsentQuestion.objects.filter(experiment=ex).values_list(
            "text", flat=True
        )
    )
    assert texts == ["First", "Second"]


def test_get_list_item_returns_none_when_no_lists(experiment_factory):
    """get_list_item returns None when experiment has no non-excluded list items."""
    ex = experiment_factory()
    assert ex.get_list_item() is None


@pytest.mark.parametrize(
    "strategy, subjects, expected_idx",
    [
        # (strategy, [(listitem_index, participant_id), ...], expected_listitem_index)
        (exp_models.Experiment.RANDOM, [], 0),
        (exp_models.Experiment.SEQUENTIAL, [], 0),
        (exp_models.Experiment.SEQUENTIAL, [(0, 1)], 1),
        (exp_models.Experiment.SEQUENTIAL, [(0, 1), (1, 2)], 0),
        (exp_models.Experiment.LEASTPLAYED, [], 0),
        (exp_models.Experiment.LEASTPLAYED, [(1, 1)], 0),
        (exp_models.Experiment.LEASTPLAYED, [(0, 1)], 1),
    ],
    ids=[
        "random",
        "sequential-no-prior-subjects",
        "sequential-subject-on-first",
        "sequential-wrap-around",
        "leastplayed-equal-counts",
        "leastplayed-one-subject-on-second",
        "leastplayed-one-subject-on-first",
    ],
)
def test_get_list_item_strategies(
    strategy,
    subjects,
    expected_idx,
    listitem_factory,
    experiment_factory,
    subjectdata_factory,
    monkeypatch,
):
    """get_list_item returns the correct ListItem for each list selection strategy."""
    ex = experiment_factory()
    lists = [
        listitem_factory(list_name="A", experiment=ex),
        listitem_factory(list_name="B", experiment=ex),
    ]
    ex.list_selection_strategy = strategy
    ex.save(update_fields=["list_selection_strategy"])
    monkeypatch.setattr("random.choice", lambda seq: seq[0])
    for listitem_idx, participant_id in subjects:
        subjectdata_factory(
            experiment=ex, listitem=lists[listitem_idx], participant_id=participant_id
        )
    result = ex.get_list_item()
    assert result == lists[expected_idx]
