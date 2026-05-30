"""Unit tests that cover reporter.py behaviour.

These tests exercise the Reporter class and its methods
- __init__ (ensure it creates an empty zipfile and sets up paths correctly)
- calc_trial_duration (test numeric and missing time inputs)
- calc_roi_response (test with various coordinate inputs and grid/resolution settings,
  including edge cases like coordinates on the boundary, or out-of-bounds coordinates)
- gcd (test with various pairs of integers, including edge cases)
- create_*_worksheet methods (test that they return the expected objects containing
  expected data, and that they handle empty datasets gracefully)
- create_report (test that it produces a .zip file with the expected structure and
  contents)
"""

import importlib
import pathlib
from types import SimpleNamespace
from zipfile import ZipFile as _RealZipFile

import pytest

# module under test
rpt = importlib.import_module("experiments.reporter")

# ---------------------------------------------------------------------------
# Sample data derived from the reference participant xlsx
# ---------------------------------------------------------------------------

_SAMPLE_XLSX = (
    pathlib.Path(__file__).parent.parent
    / "data"
    / "13_eye-tracking_test_20231006_4806daaa62534cab8d58fc441e442471.xlsx"
)

# Minimal calibration webgazer_data matching the sample xlsx:
#   [0]  - validation summary dict (includes "trial_type" dropped by the reporter)
#   [1:] - individual gaze samples {t, x, y}
_CALIBRATION_WEBGAZER_DATA = [
    # webgazer_data[0]: validation summary in dict-of-arrays format (one entry per
    # gaze sample collected at the calibration target).  The reporter reads this with
    # pd.read_json and then drops "trial_type".
    {
        "trial_type": ["webgazer_calibrate", "webgazer_calibrate", "webgazer_calibrate"],
        "x": [995.0225736782604, 991.6243043637024, 993.645883309357],
        "y": [601.6824880372583, 573.7935240063534, 576.4765554663201],
        "accuracy": [123.8960048500634, 123.8960048500634, 123.8960048500634],
        "target_x": [864, 864, 864],
        "target_y": [540, 540, 540],
        "precision_rms": [46.32411013388716, 46.32411013388716, 46.32411013388716],
        "precision_perc": [77, 77, 77],
        "precision_sd_x": [52.7248043692667, 52.7248043692667, 52.7248043692667],
        "precision_sd_y": [57.78888731895658, 57.78888731895658, 57.78888731895658],
    },
    # webgazer_data[1:]: individual gaze samples
    {"t": 32.6, "x": 511, "y": 504},
    {"t": 74.3, "x": 739, "y": 586},
    {"t": 107.9, "x": 872, "y": 630},
]


def _xlsx_sheet_columns(sheet_index):
    """Return the header row column names from the given 1-based sheet of the sample xlsx.

    Reads the xlsx as a zip of XML to avoid an openpyxl dependency.
    """
    import xml.etree.ElementTree as ET

    ns = {"ss": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with _RealZipFile(_SAMPLE_XLSX) as zf:
        shared = []
        with zf.open("xl/sharedStrings.xml") as f:
            for si in ET.parse(f).getroot().findall("ss:si", ns):
                t = si.find(".//ss:t", ns)
                shared.append(t.text if t is not None else "")
        with zf.open(f"xl/worksheets/sheet{sheet_index}.xml") as f:
            first_row = ET.parse(f).getroot().findall(".//ss:row", ns)[0]
            return [
                shared[int(c.find("ss:v", ns).text)]
                for c in first_row.findall("ss:c", ns)
            ]


class DummyZipFile:
    def __init__(self, *_, **__):
        self.written = []

    def write(self, *args, **kwargs):
        self.written.append((args, kwargs))

    def close(self):
        pass


class DummyDF:
    def __init__(self, data=None, columns=None):
        # store so tests can inspect
        self.data = data
        self.columns = columns
        self.saved = {"to_excel": False}

    def to_excel(self, *_, **__):
        self.saved["to_excel"] = True

    @staticmethod
    def from_dict(d, **__):
        return DummyDF(data=d)


class DummyExcelWriter:
    """Stub for pd.ExcelWriter that discards all operations."""

    def __init__(self, *_, **__):
        pass

    def close(self):
        pass


def make_reporter(monkeypatch, tmp_path, experiment):
    """Helper to construct a Reporter instance with heavy IO monkeypatched away."""
    monkeypatch.setattr(
        rpt, "settings", SimpleNamespace(REPORTS_ROOT=str(tmp_path)), raising=False
    )
    monkeypatch.setattr(
        "experiments.reporter.zipfile.ZipFile", DummyZipFile, raising=True
    )
    monkeypatch.setattr("experiments.reporter.pd.DataFrame", DummyDF, raising=True)
    return rpt.Reporter(experiment)


@pytest.fixture
def reporter(monkeypatch, tmp_path, experiment_factory):
    """Return a Reporter with IO patched away, backed by a real DB experiment."""
    exp = experiment_factory(exp_name="rpt-test")
    return make_reporter(monkeypatch, tmp_path, exp)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_reporter_init(monkeypatch, tmp_path, experiment_factory):
    """__init__ sets output paths correctly and wraps a zipfile."""
    exp = experiment_factory(exp_name="myexp")
    rep = make_reporter(monkeypatch, tmp_path, exp)

    assert rep.output_folder == str(tmp_path)
    assert rep.output_file == "myexp.zip"
    assert isinstance(rep.zip_file, DummyZipFile)
    assert isinstance(rep.trial_columns, list)
    assert len(rep.trial_columns) > 0


# ---------------------------------------------------------------------------
# calc_trial_duration
# ---------------------------------------------------------------------------


def test_calc_trial_duration_numeric(reporter):
    """Returns the string difference for valid float start/end times."""
    assert reporter.calc_trial_duration(1.5, 4.0) == str(4.0 - 1.5)


def test_calc_trial_duration_missing(reporter):
    """Returns an empty string when either time is None."""
    assert reporter.calc_trial_duration(None, None) == ""


# ---------------------------------------------------------------------------
# calc_roi_response
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "result_coords,expected",
    [
        ([10, 10], "(1,1)"),  # top-left quadrant
        ([99, 99], "(2,2)"),  # bottom-right quadrant
        ([50, 50], "(1,1)"),  # on boundary; x=50 satisfies c >= 50 at index 1 -> col 1
        ([0, 0], "(0,0)"),  # origin
        ([200, 200], "(2,2)"),  # out of positive bounds
        ([-10, -10], "(0,0)"),  # out of negative bounds
        ([], ""),  # required length 2 but empty
        ([10], ""),  # required length 2 but only one coordinate
    ],
)
def test_calc_roi_response(reporter, result_coords, expected):
    """Tests calc_roi_response with various coordinate inputs."""
    trial_result = SimpleNamespace(
        resolution_w=100,
        resolution_h=100,
        trialitem=SimpleNamespace(grid_row=2, grid_col=2),
    )
    assert reporter.calc_roi_response(trial_result, result_coords) == expected


# ---------------------------------------------------------------------------
# gcd
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (48, 18, 6),  # common divisor case
        (18, 48, 6),  # gcd is commutative/symmetric
        (7, 3, 1),  # coprime case
        (5, 0, 5),  # base case: gcd(a, 0) == a
        (0, 5, 5),  # base case: gcd(0, b) == b
        (0, 0, 0),  # edge case: gcd(0, 0) is conventionally defined as 0
    ],
)
def test_gcd(reporter, a, b, expected):
    """Tests gcd with various pairs of integers, including edge cases."""
    assert reporter.gcd(a, b) == expected


# ---------------------------------------------------------------------------
# create_subject_worksheet
# ---------------------------------------------------------------------------


def test_create_subject_worksheet(
    monkeypatch,
    tmp_path,
    experiment_factory,
    subjectdata_factory,
    consent_question_factory,
    question_factory,
):
    """create_subject_worksheet returns a DummyDF whose data contains expected keys,
    including consent-question and age-question entries.
    """
    exp = experiment_factory(exp_name="ws-test")
    subject = subjectdata_factory(experiment=exp)
    consent_question_factory(text="Agree?", experiment=exp, position=0)
    age_q = question_factory(
        text="DOB",
        question_type=rpt.Question.AGE,
        experiment=exp,
        position=0,
    )
    from experiments.models import AnswerText

    AnswerText.objects.create(question=age_q, subject_data=subject, body="2020-01-01")

    rep = make_reporter(monkeypatch, tmp_path, exp)
    df = rep.create_subject_worksheet(subject)

    assert isinstance(df, DummyDF)
    assert "Report Date" in df.data
    assert "Experiment Name" in df.data
    assert "Participant UUID" in df.data
    # CDI keys are always present even when no CdiResult objects exist
    assert "CDI estimate" in df.data
    # consent question key uses 1-based position prefix
    assert "1. Agree?" in df.data
    # age answer key uses 1-based position prefix
    assert "1. DOB" in df.data


def test_create_subject_worksheet_propagates_missing_answer(
    monkeypatch,
    tmp_path,
    experiment_factory,
    subjectdata_factory,
    question_factory,
):
    """ObjectDoesNotExist from a missing answer subclass row is logged and re-raised."""
    from django.core.exceptions import ObjectDoesNotExist

    from experiments.models import AnswerText

    exp = experiment_factory(exp_name="err-test")
    subject = subjectdata_factory(experiment=exp)
    question_factory(
        text="Q", question_type=rpt.Question.TEXT, experiment=exp, position=0
    )
    AnswerText.objects.create(
        question=rpt.Question.objects.get(experiment=exp),
        subject_data=subject,
        body="x",
    )
    monkeypatch.setattr(
        rpt.AnswerText.objects,
        "get",
        lambda **_: (_ for _ in ()).throw(ObjectDoesNotExist()),
    )

    rep = make_reporter(monkeypatch, tmp_path, exp)
    with pytest.raises(ObjectDoesNotExist):
        rep.create_subject_worksheet(subject)


# ---------------------------------------------------------------------------
# create_trial_worksheet / create_webgazer_worksheet  (empty datasets)
# ---------------------------------------------------------------------------


def test_create_trial_worksheet_empty(monkeypatch, tmp_path, subjectdata_factory):
    """create_trial_worksheet returns a DummyDF when there are no TrialResult rows."""
    subject = subjectdata_factory()
    rep = make_reporter(monkeypatch, tmp_path, subject.experiment)
    df = rep.create_trial_worksheet(subject)
    assert isinstance(df, DummyDF)


def test_create_webgazer_worksheet_empty(monkeypatch, tmp_path, subjectdata_factory):
    """create_webgazer_worksheet returns a (webgazer, validation) pair of DummyDFs
    when there are no gaze results.
    """
    subject = subjectdata_factory()
    rep = make_reporter(monkeypatch, tmp_path, subject.experiment)
    webgazer, validation = rep.create_webgazer_worksheet(subject)
    assert isinstance(webgazer, DummyDF)
    assert isinstance(validation, DummyDF)


# ---------------------------------------------------------------------------
# create_report
# ---------------------------------------------------------------------------


def _patch_create_report(monkeypatch, rep, subject):
    """Monkeypatch the heavy parts of create_report for a single subject."""
    monkeypatch.setattr(rep, "create_subject_worksheet", lambda _: DummyDF({"k": "v"}))
    monkeypatch.setattr(
        rep, "create_trial_worksheet", lambda _: DummyDF([], columns=rep.trial_columns)
    )
    monkeypatch.setattr(
        rep, "create_webgazer_worksheet", lambda _: [DummyDF([]), DummyDF([])]
    )
    monkeypatch.setattr(rpt.pd, "ExcelWriter", DummyExcelWriter, raising=False)
    monkeypatch.setattr(
        "experiments.reporter.SubjectData",
        SimpleNamespace(objects=SimpleNamespace(filter=lambda **_: [subject])),
        raising=False,
    )


def test_create_report_returns_path_in_reports_root(
    monkeypatch, tmp_path, subjectdata_factory
):
    """create_report returns a path string located inside REPORTS_ROOT."""
    subject = subjectdata_factory()
    rep = make_reporter(monkeypatch, tmp_path, subject.experiment)
    _patch_create_report(monkeypatch, rep, subject)

    out = rep.create_report()
    assert isinstance(out, str)
    assert str(tmp_path) in out


def test_create_report_zip_contains_xlsx(monkeypatch, tmp_path, subjectdata_factory):
    """create_report writes at least one .xlsx workbook into the zip archive."""
    subject = subjectdata_factory()
    rep = make_reporter(monkeypatch, tmp_path, subject.experiment)
    _patch_create_report(monkeypatch, rep, subject)

    rep.create_report()

    arcnames = [entry[0][1] for entry in rep.zip_file.written]
    assert any(name.endswith(".xlsx") for name in arcnames)


def test_create_report_includes_eye_tracking_worksheets(
    monkeypatch, tmp_path, subjectdata_factory
):
    """create_report calls create_webgazer_worksheet when recording_option is 'EYE'."""
    subject = subjectdata_factory()
    subject.experiment.recording_option = "EYE"
    subject.experiment.save()

    rep = make_reporter(monkeypatch, tmp_path, subject.experiment)
    webgazer_called = []

    def fake_webgazer(s):
        webgazer_called.append(s)
        return [DummyDF([]), DummyDF([])]

    monkeypatch.setattr(rep, "create_subject_worksheet", lambda _: DummyDF({"k": "v"}))
    monkeypatch.setattr(
        rep, "create_trial_worksheet", lambda _: DummyDF([], columns=rep.trial_columns)
    )
    monkeypatch.setattr(rep, "create_webgazer_worksheet", fake_webgazer)
    monkeypatch.setattr(rpt.pd, "ExcelWriter", DummyExcelWriter, raising=False)
    monkeypatch.setattr(
        "experiments.reporter.SubjectData",
        SimpleNamespace(objects=SimpleNamespace(filter=lambda **_: [subject])),
        raising=False,
    )

    rep.create_report()
    assert len(webgazer_called) == 1


# ---------------------------------------------------------------------------
# __init__ -- webcam directory creation (line 87)
# ---------------------------------------------------------------------------


def test_reporter_init_creates_webcam_dir(monkeypatch, tmp_path, experiment_factory):
    """__init__ calls os.makedirs('webcam') when the webcam directory does not exist."""
    makedirs_calls = []
    orig_makedirs = rpt.os.makedirs

    def tracking_makedirs(path, *args, **kwargs):
        makedirs_calls.append(path)
        if path != "webcam":
            orig_makedirs(path, *args, **kwargs)

    monkeypatch.setattr(rpt.os.path, "exists", lambda p: p != "webcam")
    monkeypatch.setattr(rpt.os, "makedirs", tracking_makedirs)
    monkeypatch.setattr(
        rpt, "settings", SimpleNamespace(REPORTS_ROOT=str(tmp_path)), raising=False
    )
    monkeypatch.setattr(
        "experiments.reporter.zipfile.ZipFile", DummyZipFile, raising=True
    )
    monkeypatch.setattr("experiments.reporter.pd.DataFrame", DummyDF, raising=True)

    rpt.Reporter(experiment_factory(exp_name="webcam-test"))
    assert "webcam" in makedirs_calls


# ---------------------------------------------------------------------------
# create_subject_worksheet -- question type branches (lines 158-194)
# ---------------------------------------------------------------------------


def test_create_subject_worksheet_question_types(
    monkeypatch,
    tmp_path,
    experiment_factory,
    subjectdata_factory,
    question_factory,
):
    """create_subject_worksheet includes string values for TEXT, INTEGER, RADIO,
    SELECT, and SELECT_MULTIPLE question types.
    """
    from experiments.models import (
        AnswerInteger,
        AnswerRadio,
        AnswerSelect,
        AnswerSelectMultiple,
        AnswerText,
    )

    exp = experiment_factory(exp_name="qtypes-test")
    subject = subjectdata_factory(experiment=exp)

    q_text = question_factory(
        text="Name", question_type=rpt.Question.TEXT, experiment=exp, position=0
    )
    AnswerText.objects.create(question=q_text, subject_data=subject, body="Alice")

    q_int = question_factory(
        text="Count", question_type=rpt.Question.INTEGER, experiment=exp, position=1
    )
    AnswerInteger.objects.create(question=q_int, subject_data=subject, body=5)

    q_radio = question_factory(
        text="Choice", question_type=rpt.Question.RADIO, experiment=exp, position=2
    )
    AnswerRadio.objects.create(question=q_radio, subject_data=subject, body="Option A")

    q_select = question_factory(
        text="City", question_type=rpt.Question.SELECT, experiment=exp, position=3
    )
    AnswerSelect.objects.create(question=q_select, subject_data=subject, body="London")

    q_multi = question_factory(
        text="Tags",
        question_type=rpt.Question.SELECT_MULTIPLE,
        experiment=exp,
        position=4,
    )
    AnswerSelectMultiple.objects.create(
        question=q_multi, subject_data=subject, body="a,b"
    )

    rep = make_reporter(monkeypatch, tmp_path, exp)
    df = rep.create_subject_worksheet(subject)

    assert df.data["1. Name"] == "Alice"
    assert df.data["2. Count"] == "5"
    assert df.data["3. Choice"] == "Option A"
    assert df.data["4. City"] == "London"
    assert df.data["5. Tags"] == "a,b"


def test_create_subject_worksheet_age_integer_fallback(
    monkeypatch,
    tmp_path,
    experiment_factory,
    subjectdata_factory,
    question_factory,
):
    """When an AGE question has no AnswerText, falls back to reading AnswerInteger (line 174)."""
    from experiments.models import AnswerInteger

    exp = experiment_factory(exp_name="age-int-test")
    subject = subjectdata_factory(experiment=exp)
    q_age = question_factory(
        text="Age months",
        question_type=rpt.Question.AGE,
        experiment=exp,
        position=0,
    )
    AnswerInteger.objects.create(question=q_age, subject_data=subject, body=24)

    rep = make_reporter(monkeypatch, tmp_path, exp)
    df = rep.create_subject_worksheet(subject)
    assert df.data["1. Age months"] == "24"


# ---------------------------------------------------------------------------
# create_subject_worksheet -- CdiResult loop (lines 203-204)
# ---------------------------------------------------------------------------


def test_create_subject_worksheet_cdi_results(
    monkeypatch,
    tmp_path,
    experiment_factory,
    subjectdata_factory,
):
    """CdiResult entries appear as individual keys in the subject worksheet data."""
    from experiments.models import CdiResult

    exp = experiment_factory(exp_name="cdi-test")
    subject = subjectdata_factory(experiment=exp)
    CdiResult.objects.create(subject=subject, given_label="dog", response=True)

    rep = make_reporter(monkeypatch, tmp_path, exp)
    df = rep.create_subject_worksheet(subject)
    assert "dog" in df.data
    assert df.data["dog"] is True


# ---------------------------------------------------------------------------
# create_trial_worksheet -- loop body (lines 232-283)
# ---------------------------------------------------------------------------


def test_create_trial_worksheet_with_one_result(
    monkeypatch,
    tmp_path,
    subjectdata_factory,
    outerblock_factory,
    blockitem_factory,
    trialitem_factory,
):
    """create_trial_worksheet processes a TrialResult row and writes its webcam
    file entry to the zip archive.
    """
    from django.core.files.base import ContentFile
    from filer.models.filemodels import File as FilerFile
    from experiments.models import TrialResult

    def _make_filer_file(filename):
        f = FilerFile(original_filename=filename)
        f.file.save(filename, ContentFile(b""), save=True)
        return f

    subject = subjectdata_factory()
    outerblock = outerblock_factory(listitem=subject.listitem)
    blockitem = blockitem_factory(outerblock=outerblock)
    trialitem = trialitem_factory(blockitem=blockitem)
    trialitem.visual_file = _make_filer_file("test-image.png")
    trialitem.save()
    TrialResult.objects.create(
        subject=subject, trialitem=trialitem, key_pressed=""
    )

    rep = make_reporter(monkeypatch, tmp_path, subject.experiment)
    df = rep.create_trial_worksheet(subject)

    assert isinstance(df, DummyDF)
    # zip_file.write is called once per trial result for the webcam file
    assert len(rep.zip_file.written) == 1


# ---------------------------------------------------------------------------
# create_webgazer_worksheet -- skip branch and loop body (lines 313-350)
# ---------------------------------------------------------------------------


def test_create_webgazer_worksheet_skips_gaze_disabled(
    monkeypatch,
    tmp_path,
    subjectdata_factory,
    outerblock_factory,
    blockitem_factory,
    trialitem_factory,
):
    """TrialResult rows with record_gaze=False are skipped; returns empty DFs."""
    from experiments.models import TrialResult

    subject = subjectdata_factory()
    outerblock = outerblock_factory(listitem=subject.listitem)
    blockitem = blockitem_factory(outerblock=outerblock)
    trialitem = trialitem_factory(blockitem=blockitem)
    trialitem.record_gaze = False
    trialitem.save()
    TrialResult.objects.create(subject=subject, trialitem=trialitem, key_pressed="")

    rep = make_reporter(monkeypatch, tmp_path, subject.experiment)
    webgazer, validation = rep.create_webgazer_worksheet(subject)
    assert isinstance(webgazer, DummyDF)
    assert isinstance(validation, DummyDF)


def test_create_webgazer_worksheet_non_calibration_trial(
    monkeypatch,
    tmp_path,
    subjectdata_factory,
    outerblock_factory,
    blockitem_factory,
    trialitem_factory,
):
    """create_webgazer_worksheet populates webgazer_data for a non-calibration trial.
    Expected columns are verified against the EyeTrackingData sheet of the sample xlsx.
    """
    import pandas as pd
    from experiments.models import TrialResult

    subject = subjectdata_factory()
    outerblock = outerblock_factory(listitem=subject.listitem)
    blockitem = blockitem_factory(outerblock=outerblock)
    trialitem = trialitem_factory(blockitem=blockitem)
    trialitem.record_gaze = True
    trialitem.is_calibration = False
    trialitem.save()
    TrialResult.objects.create(
        subject=subject,
        trialitem=trialitem,
        key_pressed="",
        webgazer_data=[{"x": 10, "y": 20, "t": 100}],
    )

    monkeypatch.setattr(
        rpt, "settings", SimpleNamespace(REPORTS_ROOT=str(tmp_path)), raising=False
    )
    monkeypatch.setattr(
        "experiments.reporter.zipfile.ZipFile", DummyZipFile, raising=True
    )
    rep = rpt.Reporter(subject.experiment)

    webgazer, validation = rep.create_webgazer_worksheet(subject)
    assert isinstance(webgazer, pd.DataFrame)
    assert list(webgazer.columns) == _xlsx_sheet_columns(3)  # EyeTrackingData
    assert isinstance(validation, pd.DataFrame)


def test_create_webgazer_worksheet_calibration_trial(
    monkeypatch,
    tmp_path,
    subjectdata_factory,
    outerblock_factory,
    blockitem_factory,
    trialitem_factory,
):
    """create_webgazer_worksheet splits calibration webgazer_data into a validation
    summary and gaze samples, and computes Gaze Area for a multi-cell grid.
    Output columns are verified against the sample xlsx.
    """
    import pandas as pd
    from experiments.models import TrialResult

    subject = subjectdata_factory()
    outerblock = outerblock_factory(listitem=subject.listitem)
    blockitem = blockitem_factory(outerblock=outerblock)
    trialitem = trialitem_factory(blockitem=blockitem)
    trialitem.record_gaze = True
    trialitem.is_calibration = True
    trialitem.grid_row = 3
    trialitem.grid_col = 3
    trialitem.save()
    TrialResult.objects.create(
        subject=subject,
        trialitem=trialitem,
        key_pressed="",
        webgazer_data=_CALIBRATION_WEBGAZER_DATA,
        resolution_w=1728,
        resolution_h=1117,
    )

    monkeypatch.setattr(
        rpt, "settings", SimpleNamespace(REPORTS_ROOT=str(tmp_path)), raising=False
    )
    monkeypatch.setattr(
        "experiments.reporter.zipfile.ZipFile", DummyZipFile, raising=True
    )
    rep = rpt.Reporter(subject.experiment)

    webgazer, validation = rep.create_webgazer_worksheet(subject)
    assert isinstance(webgazer, pd.DataFrame)
    assert list(webgazer.columns) == _xlsx_sheet_columns(3)   # EyeTrackingData
    assert isinstance(validation, pd.DataFrame)
    assert list(validation.columns) == _xlsx_sheet_columns(4)  # EyeTrackingValidation
