from types import SimpleNamespace
import importlib
import os
import uuid
import pytest

# module under test
rpt = importlib.import_module("ipl.experiments.reporter")


class DummyZipFile:
    def __init__(self, *args, **kwargs):
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

    def to_excel(self, writer, sheet_name=None, header=True, index=True, index_label=None):
        self.saved["to_excel"] = True

    @staticmethod
    def from_dict(d, orient="index"):
        return DummyDF(data=d)


def make_reporter(monkeypatch, tmp_path, experiment):
    """
    Helper to construct a Reporter instance with heavy IO monkeypatched away.
    """
    # Patch settings.REPORTS_ROOT used by the module
    monkeypatch.setattr(rpt, "settings", SimpleNamespace(REPORTS_ROOT=str(tmp_path)), raising=False)

    # monkeypatch zipfile.ZipFile used in Reporter.__init__
    monkeypatch.setattr("ipl.experiments.reporter.zipfile.ZipFile", DummyZipFile, raising=True)

    # monkeypatch pandas DataFrame used by reporter functions
    monkeypatch.setattr("ipl.experiments.reporter.pd.DataFrame", DummyDF, raising=True)

    # create and return reporter
    return rpt.Reporter(experiment)


def test_calc_trial_duration(monkeypatch, tmp_path, experiment_factory):
    exp = experiment_factory(exp_name="rpt-test")
    rep = make_reporter(monkeypatch, tmp_path, exp)
    # numeric start and end times (floats) -> difference converted to string
    assert rep.calc_trial_duration(1.5, 4.0) == str(4.0 - 1.5)
    # missing times -> empty string
    assert rep.calc_trial_duration(None, None) == ""


def test_calc_roi_response_basic():
    # Create a dummy result with grid 2x2 and resolution 100x100
    result = SimpleNamespace(
        resolution_w=100,
        resolution_h=100,
        trialitem=SimpleNamespace(grid_row=2, grid_col=2)
    )
    rep = rpt.Reporter(SimpleNamespace(exp_name="unused"))  # minimal experiment used only for instantiation
    # coords in top-left quadrant -> (0,0)
    assert rep.calc_roi_response(result, [10, 10]) == "(0,0)"
    # coords near bottom-right -> expect last cell (row,col) indices
    assert rep.calc_roi_response(result, [99, 99]) in ("(2,2)", "(1,1)")


def test_gcd_recursive():
    rep = rpt.Reporter(SimpleNamespace(exp_name="unused2"))
    assert rep.gcd(48, 18) == 6
    assert rep.gcd(7, 3) == 1
    # gcd with b==0 returns a
    assert rep.gcd(5, 0) == 5


def test_create_subject_worksheet(monkeypatch, tmp_path, subjectdata_factory, consent_question_factory, question_factory):
    """
    Build a minimal SubjectData with related consent question and an answer,
    then ensure create_subject_worksheet returns a DummyDF with expected data keys.
    """
    # create subject  related experiment
    subject = subjectdata_factory()
    # create a consent question for this experiment
    cq = consent_question_factory(text="Agree?", experiment=subject.experiment, position=0)
    # create an age question and corresponding AnswerText with ISO date (so code computes months)
    age_q = question_factory(text="DOB", question_type=rpt.Question.AGE, experiment=subject.experiment, position=0)
    # create an AnswerText instance for the subject; use model to persist
    from ipl.experiments.models import AnswerText
    AnswerText.objects.create(question=age_q, subject_data=subject, body="2020-01-01")
    # Prepare reporter with monkeypatched environment
    monkeypatch.setattr("ipl.experiments.reporter.zipfile.ZipFile", DummyZipFile, raising=True)
    monkeypatch.setattr("ipl.experiments.reporter.pd.DataFrame", DummyDF, raising=True)
    monkeypatch.setattr(rpt, "settings", SimpleNamespace(REPORTS_ROOT=str(tmp_path)), raising=False)
    rep = rpt.Reporter(subject.experiment)
    df = rep.create_subject_worksheet(subject)
    # DummyDF stores original dict; ensure keys include some expected fields
    assert isinstance(df, DummyDF)
    # Basic expected keys
    assert "Report Date" in df.data
    assert "Experiment Name" in df.data
    assert "Participant UUID" in df.data
    # CDI-related keys are present even if no CdiResult objects exist
    assert "CDI estimate" in df.data


def test_create_trial_and_webgazer_worksheets_empty(monkeypatch, tmp_path, subjectdata_factory):
    """
    Ensure trial/webgazer worksheet creation returns DummyDF objects and
    that create_trial_worksheet handles empty TrialResult sets gracefully.
    """
    subject = subjectdata_factory()
    monkeypatch.setattr("ipl.experiments.reporter.zipfile.ZipFile", DummyZipFile, raising=True)
    monkeypatch.setattr("ipl.experiments.reporter.pd.DataFrame", DummyDF, raising=True)
    monkeypatch.setattr(rpt, "settings", SimpleNamespace(REPORTS_ROOT=str(tmp_path)), raising=False)
    rep = rpt.Reporter(subject.experiment)

    # When there are no TrialResult rows the method should return a DummyDF for trials
    trials_df = rep.create_trial_worksheet(subject)
    assert isinstance(trials_df, DummyDF)

    # create_webgazer_worksheet should return a pair of DummyDF objects (webgazer_data, validation_data)
    webgazer, validation = rep.create_webgazer_worksheet(subject)
    assert isinstance(webgazer, DummyDF) and isinstance(validation, DummyDF)


def test_create_report_minimal(monkeypatch, tmp_path, subjectdata_factory):
    """
    Test create_report path where there is one subject and worksheet creation methods
    are monkeypatched to avoid heavy pandas/xlsxwriter operations.
    """
    subject = subjectdata_factory()
    monkeypatch.setattr(rpt, "settings", SimpleNamespace(REPORTS_ROOT=str(tmp_path)), raising=False)
    # prevent actual zipfile usage
    monkeypatch.setattr("ipl.experiments.reporter.zipfile.ZipFile", DummyZipFile, raising=True)

    # Create a Reporter but replace its worksheet builders with simple callables that return DummyDF
    rep = rpt.Reporter(subject.experiment)
    monkeypatch.setattr(rep, "create_subject_worksheet", lambda s: DummyDF({"k": "v"}))
    monkeypatch.setattr(rep, "create_trial_worksheet", lambda s: DummyDF([], columns=rep.trial_columns))
    monkeypatch.setattr(rep, "create_webgazer_worksheet", lambda s: [DummyDF([]), DummyDF([])])

    # monkeypatch SubjectData.objects.filter to return our single subject
    fake_subject_model = SimpleNamespace(objects=SimpleNamespace(filter=lambda **kw: [subject]))
    monkeypatch.setattr("ipl.experiments.reporter.SubjectData", fake_subject_model, raising=False)

    out = rep.create_report()
    assert isinstance(out, str)
    # output path should contain the REPORTS_ROOT folder path from settings
    assert str(tmp_path) in out
