"""
Unit tests that cover models.py behaviour and helpers.

These tests exercise:
- __str__ implementations
- Question.get_choices, validate_list, validate_range, and clean()
- Experiment helper methods that are model-level (subject_questions, consent_questions, get_list_item smoke checks)
- TrialResult filename property and _delete_file/delete_file receiver behavior (monkeypatched)
"""

import os
import pytest
from django.core.exceptions import ValidationError
from django.conf import settings

from experiments import models as exp_models


def test_instrument_str(instrument_factory):
    inst = instrument_factory(instr_name="My Instrument")
    assert str(inst) == "My Instrument"


def test_experiment_str_and_subject_consent_questions(experiment_factory, question_factory, consent_question_factory):
    ex = experiment_factory(exp_name="ExpName")
    q = question_factory(text="Q1", experiment=ex, position=1)
    cq = consent_question_factory(text="Agree", experiment=ex, position=1)
    assert str(ex) == "ExpName"
    # subject_questions and consent_questions should return QuerySets with our created objects
    assert q in list(ex.subject_questions())
    assert cq in list(ex.consent_questions())


def test_listitem_outerblock_blockitem_str(listitem_factory, outerblock_factory, blockitem_factory):
    li = listitem_factory(list_name="MyList")
    assert str(li) == "MyList"
    ob = outerblock_factory(listitem=li, outer_block_name="O1", position=1)
    bi = blockitem_factory(outerblock=ob, label="B1", position=1)
    assert str(ob) == "O1"
    assert str(bi) == "B1"


def test_trialitem_and_trialresult_and_filename(trialitem_factory, trialresult_factory):
    ti = trialitem_factory(label="T1")
    tr = trialresult_factory(trialitem=ti, webcam_name="uploads/exp/list/visual/cam.png")
    assert str(ti) == "T1"
    assert tr.filename == "cam.png"


def test__delete_file_and_delete_file_signal(monkeypatch, trialresult_factory, tmp_path):
    from experiments.models import _delete_file, delete_file
    dummy_path = "/tmp/somefile.to.delete"
    removed = {"ok": False}

    monkeypatch.setattr("os.path.isfile", lambda p: True if p == dummy_path else False)
    def fake_remove(p):
        if p == dummy_path:
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
    q_range = question_factory(question_type=exp_models.Question.NUM_RANGE, choices="1, 10")
    # should not raise
    q_range.clean()


def test_get_list_item_strategies(listitem_factory, experiment_factory, subjectdata_factory, monkeypatch):
    ex = experiment_factory()
    l1 = listitem_factory(list_name="A", experiment=ex)
    l2 = listitem_factory(list_name="B", experiment=ex)
    # random strategy: monkeypatch random.choice for deterministic test
    import random
    ids = list(exp_models.ListItem.objects.filter(experiment=ex).order_by("id").values_list("id", flat=True))
    monkeypatch.setattr("random.choice", lambda seq: seq[0])
    res = ex.get_list_item()
    assert res.pk in ids
    # sequential strategy
    ex.list_selection_strategy = exp_models.Experiment.SEQUENTIAL
    ex.save(update_fields=["list_selection_strategy"])
    subjectdata_factory(experiment=ex, listitem=l1)
    seq_item = ex.get_list_item()
    assert seq_item is not None
    # least played strategy
    ex.list_selection_strategy = exp_models.Experiment.LEASTPLAYED
    ex.save(update_fields=["list_selection_strategy"])
    subjectdata_factory(experiment=ex, listitem=l1)
    lp_item = ex.get_list_item()
    assert lp_item is not None