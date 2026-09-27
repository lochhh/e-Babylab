"""Unit tests that cover models.py behaviour and helpers.

These tests exercise:
- visual_folder, audio_folder helper functions
- model __str__ methods for all models
- OuterBlockItem, BlockItem, TrialItem, ConsentQuestion ordering
- Question.get_choices, validate_list, validate_range, and clean()
- Instrument.clean() CSV-only file validation
- Experiment helper methods that are model-level
- TrialResult filename property and _delete_file/delete_file receiver behavior
"""

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from experiments import models as exp_models

# ---------------------------------------------------------------------------
# Folder helper functions
# ---------------------------------------------------------------------------


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
    """Verify Instrument __str__ returns the instrument name."""
    inst = instrument_factory(instr_name="My Instrument")
    assert str(inst) == "My Instrument"


@pytest.mark.django_db
def test_deleting_instrument_nullifies_experiment_fk(
    instrument_factory, experiment_factory
):
    """Deleting an Instrument sets experiment.instrument to NULL, not cascade-deletes.

    The experiment itself must survive the deletion of its instrument.
    """
    instr = instrument_factory()
    exp = experiment_factory()
    exp.instrument = instr
    exp.save()

    instr.delete()

    exp.refresh_from_db()
    assert exp.instrument is None


# ---------------------------------------------------------------------------
# Instrument.clean() — CSV-only validation
# ---------------------------------------------------------------------------


def test_instrument_clean_accepts_all_csv(instrument_factory):
    """clean() does not raise when all file fields reference .csv files."""
    inst = instrument_factory()
    inst.clean()  # must not raise


def test_instrument_clean_rejects_non_csv(db):
    """clean() raises ValidationError when a non-.csv file is attached."""
    from django.core.files.base import ContentFile
    from filer.models.filemodels import File as FilerFile

    def make_filer_file(name):
        f = FilerFile(original_filename=name)
        f.file.save(name, ContentFile(b""), save=True)
        return f

    csv = make_filer_file("data.csv")
    bad = make_filer_file("data.xlsx")

    inst = exp_models.Instrument.objects.create(
        instr_name="test",
        words_list=bad,
        irt_params=csv,
        f_lm_np_mean=csv,
        f_lm_np_sd=csv,
        f_lm_p_mean=csv,
        f_lm_p_sd=csv,
        f_bmin=csv,
        f_slope=csv,
        m_lm_np_mean=csv,
        m_lm_np_sd=csv,
        m_lm_p_mean=csv,
        m_lm_p_sd=csv,
        m_bmin=csv,
        m_slope=csv,
    )
    with pytest.raises(ValidationError) as exc_info:
        inst.clean()
    assert "words_list" in exc_info.value.message_dict
    assert "irt_params" not in exc_info.value.message_dict


def test_instrument_clean_reports_all_offending_fields(db):
    """clean() collects errors for every non-.csv field, not just the first."""
    from django.core.files.base import ContentFile
    from filer.models.filemodels import File as FilerFile

    def make_filer_file(name):
        f = FilerFile(original_filename=name)
        f.file.save(name, ContentFile(b""), save=True)
        return f

    bad = make_filer_file("bad.txt")

    inst = exp_models.Instrument.objects.create(
        instr_name="test",
        words_list=bad,
        irt_params=bad,
        f_lm_np_mean=make_filer_file("a.csv"),
        f_lm_np_sd=make_filer_file("b.csv"),
        f_lm_p_mean=make_filer_file("c.csv"),
        f_lm_p_sd=make_filer_file("d.csv"),
        f_bmin=make_filer_file("e.csv"),
        f_slope=make_filer_file("f.csv"),
        m_lm_np_mean=make_filer_file("g.csv"),
        m_lm_np_sd=make_filer_file("h.csv"),
        m_lm_p_mean=make_filer_file("i.csv"),
        m_lm_p_sd=make_filer_file("j.csv"),
        m_bmin=make_filer_file("k.csv"),
        m_slope=make_filer_file("l.csv"),
    )
    with pytest.raises(ValidationError) as exc_info:
        inst.clean()
    errors = exc_info.value.message_dict
    assert "words_list" in errors
    assert "irt_params" in errors


def test_instrument_clean_skips_null_fields(db):
    """clean() does not raise for file fields that are null."""
    inst = exp_models.Instrument.objects.create(instr_name="empty")
    inst.clean()  # all fields null — must not raise


# ---------------------------------------------------------------------------
# _validate_file_extension helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename, allowed, expect_error",
    [
        ("data.csv", {".csv"}, False),  # allowed extension
        ("data.CSV", {".csv"}, False),  # case-insensitive match
        (None, {".csv"}, False),  # null file skipped
        ("data.xlsx", {".csv"}, True),  # disallowed extension
    ],
    ids=["allowed", "case-insensitive", "null-file", "disallowed"],
)
def test_validate_file_extension(filename, allowed, expect_error):
    """_validate_file_extension adds an error only for disallowed extensions."""

    class FakeFile:
        def __init__(self, name):
            self.original_filename = name

    filer_file = FakeFile(filename) if filename is not None else None
    errors = {}
    exp_models._validate_file_extension(filer_file, allowed, "field", errors)
    if expect_error:
        assert "field" in errors
    else:
        assert errors == {}


# ---------------------------------------------------------------------------
# TrialItem.clean() — audio/visual file extension validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", ["sound.mp3", "track.wav"])
def test_trialitem_clean_accepts_valid_audio(
    filename, filer_file_factory, trialitem_factory
):
    """clean() does not raise for allowed audio extensions."""
    trial = trialitem_factory()
    trial.audio_file = filer_file_factory(filename)
    trial.save()
    trial.clean()


@pytest.mark.parametrize(
    "filename",
    [
        "image.png",
        "photo.jpg",
        "photo.jpeg",
        "anim.gif",
        "clip.mp4",
        "clip.ogg",
        "clip.webm",
    ],
)
def test_trialitem_clean_accepts_valid_visual(
    filename, filer_file_factory, trialitem_factory
):
    """clean() does not raise for allowed visual extensions."""
    trial = trialitem_factory()
    trial.visual_file = filer_file_factory(filename)
    trial.save()
    trial.clean()


def test_trialitem_clean_rejects_bad_audio(filer_file_factory, trialitem_factory):
    """clean() raises ValidationError on audio_file with disallowed extension."""
    trial = trialitem_factory()
    trial.audio_file = filer_file_factory("sound.pdf")
    trial.save()
    with pytest.raises(ValidationError) as exc_info:
        trial.clean()
    assert "audio_file" in exc_info.value.message_dict


def test_trialitem_clean_rejects_bad_visual(filer_file_factory, trialitem_factory):
    """clean() raises ValidationError on visual_file with disallowed extension."""
    trial = trialitem_factory()
    trial.visual_file = filer_file_factory("image.csv")
    trial.save()
    with pytest.raises(ValidationError) as exc_info:
        trial.clean()
    assert "visual_file" in exc_info.value.message_dict


def test_trialitem_clean_reports_both_bad_fields(filer_file_factory, trialitem_factory):
    """clean() collects errors for both fields when both are invalid."""
    trial = trialitem_factory()
    trial.audio_file = filer_file_factory("bad.pdf")
    trial.visual_file = filer_file_factory("bad.pdf")
    trial.save()
    with pytest.raises(ValidationError) as exc_info:
        trial.clean()
    errors = exc_info.value.message_dict
    assert "audio_file" in errors
    assert "visual_file" in errors


def test_trialitem_clean_skips_null_files(trialitem_factory):
    """clean() does not raise when audio_file and visual_file are null."""
    trial = trialitem_factory()
    trial.clean()  # both null — must not raise


def test_experiment_str_and_subject_consent_questions(
    experiment_factory, question_factory, consent_question_factory
):
    """Verify Experiment __str__ and subject/consent question querysets."""
    ex = experiment_factory(exp_name="ExpName")
    q = question_factory(text="Q1", experiment=ex, position=1)
    cq = consent_question_factory(text="Agree", experiment=ex, position=1)
    assert str(ex) == "ExpName"
    # Both queryset methods should return QuerySets with the created objects.
    assert q in list(ex.subject_questions())
    assert cq in list(ex.consent_questions())


def test_listitem_outerblock_blockitem_str(
    listitem_factory, outerblock_factory, blockitem_factory
):
    """Verify __str__ returns the label for ListItem, OuterBlockItem, and BlockItem."""
    li = listitem_factory(list_name="MyList")
    assert str(li) == "MyList"
    ob = outerblock_factory(listitem=li, outer_block_name="O1", position=1)
    bi = blockitem_factory(outerblock=ob, label="B1", position=1)
    assert str(ob) == "O1"
    assert str(bi) == "B1"


def test_trialitem_and_trialresult_and_filename(trialitem_factory, trialresult_factory):
    """Verify TrialItem __str__ and TrialResult filename property."""
    ti = trialitem_factory(label="T1")
    tr = trialresult_factory(
        trialitem=ti, webcam_name="uploads/exp/list/visual/cam.png"
    )
    assert str(ti) == "T1"
    assert tr.filename == "cam.png"


def test__delete_file_and_delete_file_signal(
    monkeypatch, trialresult_factory, tmp_path
):
    """Verify _delete_file removes a file and the delete_file signal calls os.remove."""
    from experiments.models import _delete_file, delete_file

    dummy_path = "/tmp/somefile.to.delete"
    removed = {"ok": False}

    monkeypatch.setattr("os.path.isfile", lambda p: p == dummy_path)

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
    """Verify Question.get_choices, validate_list, validate_range, and clean()."""
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


# ---------------------------------------------------------------------------
# TrialItem attention getter / dwell check
# ---------------------------------------------------------------------------


@pytest.fixture
def ag_pair(trialitem_factory, attention_getter_factory):
    """Return a normal trial and a flagged attention getter in the same list."""
    trial = trialitem_factory(label="T1")
    ag = attention_getter_factory(trial, link=False)
    return trial, ag


@pytest.mark.django_db
def test_trialitem_clean_accepts_dwell_check(ag_pair, filer_file_factory):
    """A trial with an attention getter and a minimum dwell time is valid."""
    trial, ag = ag_pair
    trial.visual_file = filer_file_factory("image.jpg")
    trial.attention_getter = ag
    trial.min_dwell_time = 500
    trial.full_clean()


def _other_list_ag(trial, ag, trialitem_factory):
    other = trialitem_factory(label="AG2", code="AG2")  # new experiment/list
    other.is_attention_getter = True
    other.save()
    trial.attention_getter = other
    trial.min_dwell_time = 500


def _ag_without_dwell(t, ag):
    t.attention_getter = ag


def _dwell_without_ag(t, ag):
    t.min_dwell_time = 500


def _target_not_flagged(t, ag):
    ag.is_attention_getter = False
    ag.save()
    t.attention_getter = ag
    t.min_dwell_time = 500


def _calibration_with_dwell(t, ag):
    t.attention_getter = ag
    t.min_dwell_time = 500
    t.is_calibration = True


def _record_gaze_off(t, ag):
    t.attention_getter = ag
    t.min_dwell_time = 500
    t.record_gaze = False


def _cell_missing_row_col(t, ag):
    # non-square, non-1x1 grid so the "missing row/col" check fires instead
    # of the 1x1-grid check.
    t.grid_row, t.grid_col = 1, 2
    t.dwell_target_type = "CELL"


def _cell_row_out_of_grid(t, ag):
    t.grid_row, t.grid_col = 1, 2
    t.dwell_target_type = "CELL"
    t.dwell_target_row, t.dwell_target_col = 2, 1


def _cell_col_out_of_grid(t, ag):
    t.grid_row, t.grid_col = 2, 1
    t.dwell_target_type = "CELL"
    t.dwell_target_row, t.dwell_target_col = 1, 2


def _cell_on_1x1_grid(t, ag):
    t.dwell_target_type = "CELL"  # grid stays the factory default, 1x1


def _ag_nested_dwell(t, ag):
    ag.attention_getter = ag
    ag.min_dwell_time = 500


def _grid_row_zero(t, ag):
    t.grid_row = 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "mutate,message",
    [
        pytest.param(_ag_without_dwell, "or neither", id="ag-without-dwell"),
        pytest.param(_dwell_without_ag, "or neither", id="dwell-without-ag"),
        pytest.param(
            _target_not_flagged,
            "marked as an attention getter",
            id="target-not-flagged",
        ),
        pytest.param(_calibration_with_dwell, "calibration", id="calibration"),
        pytest.param(
            _record_gaze_off,
            "need eye-tracking",
            id="record-gaze-off",
        ),
        pytest.param(
            _cell_missing_row_col,
            "target row and column",
            id="cell-missing-row-col",
        ),
        pytest.param(
            _cell_row_out_of_grid, "only has 1 row", id="cell-row-out-of-grid"
        ),
        pytest.param(
            _cell_col_out_of_grid,
            "only has 1 column",
            id="cell-col-out-of-grid",
        ),
        pytest.param(_cell_on_1x1_grid, "grid rows/columns", id="cell-on-1x1-grid"),
        pytest.param(
            _ag_nested_dwell,
            "cannot have its own dwell check",
            id="ag-nested",
        ),
        pytest.param(_grid_row_zero, "greater than or equal to 1", id="grid-row-zero"),
    ],
)
def test_trialitem_clean_rejects_invalid_dwell_config(ag_pair, mutate, message):
    """Invalid dwell-check configurations raise a ValidationError naming the problem."""
    trial, ag = ag_pair
    mutate(trial, ag)
    target = ag if ag.attention_getter_id else trial
    with pytest.raises(ValidationError, match=message):
        target.full_clean()


@pytest.mark.django_db
def test_trialitem_clean_rejects_attention_getter_from_other_list(
    ag_pair, trialitem_factory
):
    """The attention getter must belong to the same list as the trial."""
    trial, ag = ag_pair
    _other_list_ag(trial, ag, trialitem_factory)
    with pytest.raises(ValidationError, match="same list"):
        trial.full_clean()


@pytest.mark.django_db
def test_trialitem_clean_rejects_unflagging_referenced_attention_getter(ag_pair):
    """A trial cannot stop being an attention getter while trials still use it."""
    trial, ag = ag_pair
    trial.attention_getter, trial.min_dwell_time = ag, 500
    trial.save()
    ag.is_attention_getter = False
    with pytest.raises(ValidationError, match="T1"):
        ag.full_clean()


@pytest.mark.django_db
def test_trialitem_db_constraint_rejects_half_dwell_check(ag_pair):
    """The database refuses a dwell threshold without an attention getter."""
    trial, _ = ag_pair
    with pytest.raises(IntegrityError), transaction.atomic():
        type(trial).objects.filter(pk=trial.pk).update(min_dwell_time=500)


@pytest.mark.django_db
def test_deleting_referenced_attention_getter_is_protected(ag_pair):
    """An attention getter in use cannot be deleted."""
    trial, ag = ag_pair
    trial.attention_getter, trial.min_dwell_time = ag, 500
    trial.save()
    with pytest.raises(ProtectedError):
        ag.delete()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "target_type,row,col,expected",
    [
        pytest.param("ANY", None, None, None, id="any"),
        pytest.param("CELL", 1, 2, (1, 2), id="cell"),
    ],
)
def test_trialitem_dwell_target(trialitem_factory, target_type, row, col, expected):
    """dwell_target is None for ANY and the (row, col) cell for CELL."""
    trial = trialitem_factory()
    trial.dwell_target_type, trial.dwell_target_row, trial.dwell_target_col = (
        target_type,
        row,
        col,
    )
    assert trial.dwell_target == expected
