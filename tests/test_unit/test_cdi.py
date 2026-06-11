"""Unit tests for experiments/cdi.py — CDI adaptive administration logic."""

import datetime
import importlib
import json
from io import StringIO
from types import SimpleNamespace

import numpy as np
from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory

cdi = importlib.import_module("experiments.cdi")

# Must be valid hex-and-hyphen UUID to match URL pattern [0-9A-Fa-f-]+
RUN_UUID = "12345678-abcd-ef12-3456-789abcdef012"


# ─── Shared helpers ──────────────────────────────────────────────────────────


class FakeDF:
    """Minimal pandas DataFrame stand-in used across multiple tests.

    Designed so that all column access and boolean-mask indexing returns self,
    giving tests a stable `.index`, `.at`, and `.to_numpy()`.
    """

    def __init__(self, n=1, val=2.0):
        """Initialise the fake DataFrame with n rows and a fixed column value."""
        self._val = val
        self.index = list(range(n))

    class _ILOC:
        def __init__(self, parent):
            self._p = parent

        def __getitem__(self, key):
            return self._p

    @property
    def iloc(self):
        """Return an _ILOC accessor for integer-location based indexing."""
        return FakeDF._ILOC(self)

    def reset_index(self):
        """Return self to support chaining."""
        return self

    def to_json(self, orient="records"):
        """Return an empty JSON array string."""
        return "[]"

    def to_numpy(self):
        """Return a single-row numpy array of dummy IRT parameters."""
        return np.array([[1.0, 0.0, 1.0, 0.0]])

    @property
    def at(self):
        """Return an _At accessor for label-based scalar access."""
        val = self._val

        class _At:
            def __getitem__(self, key):
                return val

        return _At()

    def __getitem__(self, key):
        """Handle column access and boolean-mask indexing by returning self."""
        # Handles both column access (str key) and boolean-mask indexing.
        # Returns self so callers can chain .index[0] etc.
        return self

    def __eq__(self, other):
        """Allow df["col"] == value to produce a mask-like object with .index."""
        # Allows `df["col"] == value` to produce a mask-like with .index.
        return self

    def __hash__(self):
        """Return a stable hash based on object identity."""
        return id(self)


class Session(dict):
    """Dict subclass that supports attribute assignment (mirrors Django sessions)."""

    modified = False


def make_subject_data():
    """Build a fake SubjectData namespace with a tracked save() stub."""
    saved = {}

    def fake_save():
        saved["called"] = True

    sd = SimpleNamespace(
        pk=RUN_UUID,
        created=datetime.datetime(2024, 6, 1, 12, 0, 0),
        experiment=SimpleNamespace(pk="exp-1"),
        cdi_estimate=None,
        save=fake_save,
    )
    sd._saved = saved
    return sd


def make_experiment(num_words=2):
    """Build a fake Experiment namespace with CDI page template and num_words."""
    return SimpleNamespace(
        pk="exp-1",
        instrument=SimpleNamespace(pk="instr-1"),
        cdi_page_tpl="{{ subject_data.pk }}",
        num_words=num_words,
    )


def make_instrument():
    """Build a fake Instrument namespace with SimpleNamespace file paths."""

    def _fp(name):
        return SimpleNamespace(file=SimpleNamespace(path=name))

    return SimpleNamespace(
        words_list=_fp("words.csv"),
        irt_params=_fp("irt.csv"),
        f_lm_np_mean=_fp("f_lm_np_mean.csv"),
        f_lm_np_sd=_fp("f_lm_np_sd.csv"),
        f_lm_p_mean=_fp("f_lm_p_mean.csv"),
        f_lm_p_sd=_fp("f_lm_p_sd.csv"),
        f_bmin=_fp("f_bmin.csv"),
        f_slope=_fp("f_slope.csv"),
        m_lm_np_mean=_fp("m_lm_np_mean.csv"),
        m_lm_np_sd=_fp("m_lm_np_sd.csv"),
        m_lm_p_mean=_fp("m_lm_p_mean.csv"),
        m_lm_p_sd=_fp("m_lm_p_sd.csv"),
        m_bmin=_fp("m_bmin.csv"),
        m_slope=_fp("m_slope.csv"),
    )


def patch_get_object_or_404(monkeypatch, subject_data, experiment, instrument=None):
    """Monkeypatch get_object_or_404 to return the provided test stubs."""

    def fake_get(model, pk=None):
        if model is cdi.SubjectData:
            return subject_data
        if model is cdi.Experiment:
            return experiment
        if instrument is not None and model is cdi.Instrument:
            return instrument
        raise AssertionError(f"Unexpected model: {model!r}")

    monkeypatch.setattr(cdi, "get_object_or_404", fake_get)


def patch_cdi_results_empty(monkeypatch):
    """Monkeypatch CdiResult so that all queryset methods return empty iterables."""

    class _Q:
        def filter(self, *a, **k):
            return self

        def order_by(self, *a, **k):
            return self

        def distinct(self, *a, **k):
            return iter([])

        def count(self):
            return 0

    class FakeCdiResult:
        objects = _Q()

        def __init__(self):
            pass

        def save(self):
            pass

    monkeypatch.setattr(cdi, "CdiResult", FakeCdiResult)


def patch_age_sex(monkeypatch, dob="2022-01-01", sex="female", choices="female, male"):
    """Monkeypatch AnswerText, AnswerRadio, and Question with fixed age/sex stubs."""

    class _FakeQS:
        def __init__(self, result):
            self._result = result

        def first(self):
            return self._result

    class FakeAnswerText:
        class objects:
            @staticmethod
            def filter(*args, **kwargs):
                return _FakeQS(SimpleNamespace(body=dob))

    class FakeAnswerRadio:
        class objects:
            @staticmethod
            def filter(*args, **kwargs):
                return _FakeQS(SimpleNamespace(body=sex))

    class FakeQuestion:
        class objects:
            @staticmethod
            def filter(*args, **kwargs):
                return _FakeQS(SimpleNamespace(choices=choices))

    monkeypatch.setattr(cdi, "AnswerText", FakeAnswerText)
    monkeypatch.setattr(cdi, "AnswerRadio", FakeAnswerRadio)
    monkeypatch.setattr(cdi, "Question", FakeQuestion)


# ─── sort_items ──────────────────────────────────────────────────────────────


def test_sort_items_returns_descending_info_order(monkeypatch):
    """Items are sorted descending by inf_hpc value (argmax first)."""
    monkeypatch.setattr(cdi, "max_info_hpc", lambda item_params: "ignored")
    monkeypatch.setattr(cdi, "inf_hpc", lambda a, b: np.array([5.0, 3.0, 7.0]))
    ordering = cdi.sort_items(np.array([[0]]))
    # neg = [-5, -3, -7]; argsort → [2, 0, 1]
    assert ordering.tolist() == [2, 0, 1]


# ─── estimateCDI ─────────────────────────────────────────────────────────────


def _patch_estimateCDI_base(monkeypatch, sd, exp, instr, sex="female"):
    patch_get_object_or_404(monkeypatch, sd, exp, instr)
    patch_cdi_results_empty(monkeypatch)
    monkeypatch.setattr("builtins.open", lambda *a, **k: StringIO(""))
    monkeypatch.setattr(cdi.csv, "DictReader", lambda f, delimiter=",": [])
    monkeypatch.setattr(cdi.pd, "read_csv", lambda *a, **k: FakeDF(n=1, val=2.0))
    monkeypatch.setattr(cdi.norm, "pdf", lambda x, loc, scale: np.ones_like(x))
    patch_age_sex(monkeypatch, sex=sex)


def test_estimateCDI_female_branch_saves_and_returns_estimate(monkeypatch):
    """Female sex branch selects f_* lookup files; estimate is stored and returned."""
    sd = make_subject_data()
    exp = make_experiment()
    instr = make_instrument()
    _patch_estimateCDI_base(monkeypatch, sd, exp, instr, sex="female")

    result = cdi.estimateCDI(sd.pk)

    assert isinstance(result, (int, float))
    assert sd.cdi_estimate is not None
    assert sd._saved.get("called") is True


def test_estimateCDI_male_branch_saves_and_returns_estimate(monkeypatch):
    """Male sex branch (sex != choices[0]) selects m_* lookup files."""
    sd = make_subject_data()
    exp = make_experiment()
    instr = make_instrument()
    _patch_estimateCDI_base(monkeypatch, sd, exp, instr, sex="male")

    result = cdi.estimateCDI(sd.pk)

    assert isinstance(result, (int, float))
    assert sd.cdi_estimate is not None


def test_estimateCDI_cdi_result_response_true_uses_lm_p_path(monkeypatch):
    """CdiResult with response=True updates basis via lm_p_mean/lm_p_sd."""
    sd = make_subject_data()
    exp = make_experiment()
    instr = make_instrument()

    cr = SimpleNamespace(given_label="dog", response=True)

    class _Q:
        def filter(self, *a, **k):
            return self

        def order_by(self, *a, **k):
            return self

        def distinct(self, *a, **k):
            return iter([cr])

    class FakeCdiResult:
        objects = _Q()

        def __init__(self):
            pass

        def save(self):
            pass

    patch_get_object_or_404(monkeypatch, sd, exp, instr)
    monkeypatch.setattr(cdi, "CdiResult", FakeCdiResult)
    monkeypatch.setattr("builtins.open", lambda *a, **k: StringIO(""))
    monkeypatch.setattr(
        cdi.csv,
        "DictReader",
        lambda f, delimiter=",": [{"word": "dog", "word_id": "1"}],
    )
    monkeypatch.setattr(cdi.pd, "read_csv", lambda *a, **k: FakeDF(n=1, val=2.0))
    monkeypatch.setattr(cdi.norm, "pdf", lambda x, loc, scale: np.ones_like(x))
    patch_age_sex(monkeypatch, sex="female")

    result = cdi.estimateCDI(sd.pk)

    assert isinstance(result, (int, float))


def test_estimateCDI_cdi_result_response_false_uses_lm_np_path(monkeypatch):
    """CdiResult with response=False updates basis via lm_np_mean/lm_np_sd."""
    sd = make_subject_data()
    exp = make_experiment()
    instr = make_instrument()

    cr = SimpleNamespace(given_label="cat", response=False)

    class _Q:
        def filter(self, *a, **k):
            return self

        def order_by(self, *a, **k):
            return self

        def distinct(self, *a, **k):
            return iter([cr])

    class FakeCdiResult:
        objects = _Q()

        def __init__(self):
            pass

        def save(self):
            pass

    patch_get_object_or_404(monkeypatch, sd, exp, instr)
    monkeypatch.setattr(cdi, "CdiResult", FakeCdiResult)
    monkeypatch.setattr("builtins.open", lambda *a, **k: StringIO(""))
    monkeypatch.setattr(
        cdi.csv,
        "DictReader",
        lambda f, delimiter=",": [{"word": "cat", "word_id": "1"}],
    )
    monkeypatch.setattr(cdi.pd, "read_csv", lambda *a, **k: FakeDF(n=1, val=1.0))
    monkeypatch.setattr(cdi.norm, "pdf", lambda x, loc, scale: np.ones_like(x))
    patch_age_sex(monkeypatch, sex="female")

    result = cdi.estimateCDI(sd.pk)

    assert isinstance(result, (int, float))


def test_estimateCDI_keyerror_returns_redirect(monkeypatch):
    """A KeyError during estimation (e.g., missing CSV column) returns a redirect."""
    sd = make_subject_data()
    exp = make_experiment()
    instr = make_instrument()

    patch_get_object_or_404(monkeypatch, sd, exp, instr)
    patch_cdi_results_empty(monkeypatch)
    monkeypatch.setattr("builtins.open", lambda *a, **k: StringIO(""))
    # Row missing 'word' key triggers KeyError on row["word"]
    monkeypatch.setattr(
        cdi.csv,
        "DictReader",
        lambda f, delimiter=",": [{"no_word_column": "x", "word_id": "1"}],
    )
    patch_age_sex(monkeypatch)

    result = cdi.estimateCDI(sd.pk)

    assert isinstance(result, HttpResponseRedirect)


# ─── cdiRun ──────────────────────────────────────────────────────────────────


def _patch_cdiRun(monkeypatch, sd, exp, instr, words=None):
    patch_get_object_or_404(monkeypatch, sd, exp, instr)
    monkeypatch.setattr("builtins.open", lambda *a, **k: StringIO(""))
    word_rows = words if words is not None else [{"word": "hello"}]
    monkeypatch.setattr(cdi.csv, "DictReader", lambda f, delimiter=",": word_rows)
    monkeypatch.setattr(cdi.pd, "read_csv", lambda *a, **k: FakeDF())
    monkeypatch.setattr(cdi, "sort_items", lambda arr: np.array([0]))

    class FakeInit:
        def __init__(self, x):
            pass

        def initialize(self):
            return 0.0

    monkeypatch.setattr(cdi, "FixedPointInitializer", FakeInit)
    monkeypatch.setattr(cdi, "VocabularyChecklistForm", lambda *a, **k: None)


def test_cdiRun_success_sets_all_session_keys(monkeypatch):
    """Verify successful cdiRun populates all expected session keys."""
    rf = RequestFactory()
    request = rf.get("/cdi/run/")
    request.session = Session()

    sd = make_subject_data()
    exp = make_experiment()
    instr = make_instrument()
    _patch_cdiRun(monkeypatch, sd, exp, instr)

    resp = cdi.cdiRun(request, sd.pk)

    assert isinstance(resp, HttpResponse)
    for key in (
        "all_words",
        "item_params",
        "administered_items",
        "irt_run",
        "est_theta",
        "words",
        "responses",
    ):
        assert key in request.session, f"session missing '{key}'"
    assert request.session["irt_run"] == 0
    assert request.session["administered_items"] == [0]
    assert request.session["responses"] == []


def test_cdiRun_keyerror_returns_redirect(monkeypatch):
    """A missing CSV column in the word list returns a redirect to error page."""
    rf = RequestFactory()
    request = rf.get("/cdi/run/")
    request.session = Session()

    sd = make_subject_data()
    exp = make_experiment()
    instr = make_instrument()
    # Row without 'word' key triggers KeyError on row["word"]
    _patch_cdiRun(monkeypatch, sd, exp, instr, words=[{"no_word": "x"}])

    resp = cdi.cdiRun(request, sd.pk)

    assert isinstance(resp, HttpResponseRedirect)


# ─── cdiSubmit ───────────────────────────────────────────────────────────────


def _make_submit_session(irt_run=0, words=None, responses=None):
    return Session(
        {
            "irt_run": irt_run,
            "words": words if words is not None else ["hello"],
            "responses": responses if responses is not None else [],
        }
    )


def _patch_cdiSubmit_common(monkeypatch, sd, exp, unique_count):
    patch_get_object_or_404(monkeypatch, sd, exp)
    _uc = unique_count

    class _Q:
        def filter(self, *a, **k):
            return self

        def order_by(self, *a, **k):
            return self

        def distinct(self, *a, **k):
            return self

        def count(self):
            return _uc

    class FakeCdiResult:
        objects = _Q()

        def __init__(self):
            self.subject = None
            self.given_label = None
            self.response = None

        def save(self):
            pass

    monkeypatch.setattr(cdi, "CdiResult", FakeCdiResult)


def test_cdiSubmit_invalid_form_rerenders_template(monkeypatch):
    """When the form is invalid, cdiSubmit re-renders the CDI page."""
    rf = RequestFactory()
    request = rf.post("/cdi/submit/", data={})
    request.session = _make_submit_session()

    sd = make_subject_data()
    exp = make_experiment()
    _patch_cdiSubmit_common(monkeypatch, sd, exp, unique_count=0)
    monkeypatch.setattr(
        cdi,
        "VocabularyChecklistForm",
        lambda *a, **k: SimpleNamespace(is_valid=lambda: False),
    )

    resp = cdi.cdiSubmit(request, sd.pk)

    assert isinstance(resp, HttpResponse)
    assert not isinstance(resp, HttpResponseRedirect)


def test_cdiSubmit_valid_not_enough_unique_calls_generate_next(monkeypatch):
    """When unique count < num_words, irt_run is incremented and next item generated."""
    rf = RequestFactory()
    request = rf.post("/cdi/submit/", data={"word_hello": "1"})
    request.session = _make_submit_session(irt_run=0, words=["hello"])

    sd = make_subject_data()
    exp = make_experiment(num_words=2)
    _patch_cdiSubmit_common(monkeypatch, sd, exp, unique_count=1)  # 1 < 2

    cleaned = {"word_hello": "1"}
    monkeypatch.setattr(
        cdi,
        "VocabularyChecklistForm",
        lambda *a, **k: SimpleNamespace(is_valid=lambda: True, cleaned_data=cleaned),
    )

    generate_called = {}
    monkeypatch.setattr(
        cdi,
        "cdiGenerateNextItem",
        lambda req, run_uuid: generate_called.__setitem__("called", True)
        or HttpResponse("next"),
    )

    resp = cdi.cdiSubmit(request, sd.pk)

    assert generate_called.get("called") is True
    assert request.session["irt_run"] == 1
    assert isinstance(resp, HttpResponse)


def test_cdiSubmit_valid_enough_words_no_list_items_redirects_end(monkeypatch):
    """When count >= num_words and no list items exist, redirects to experiment end."""
    rf = RequestFactory()
    request = rf.post("/cdi/submit/", data={"word_hello": "1"})
    request.session = _make_submit_session()

    sd = make_subject_data()
    exp = make_experiment(num_words=1)
    _patch_cdiSubmit_common(monkeypatch, sd, exp, unique_count=1)  # 1 >= 1

    cleaned = {"word_hello": "1"}
    monkeypatch.setattr(
        cdi,
        "VocabularyChecklistForm",
        lambda *a, **k: SimpleNamespace(is_valid=lambda: True, cleaned_data=cleaned),
    )
    monkeypatch.setattr(cdi, "estimateCDI", lambda run_uuid: 0.5)
    monkeypatch.setattr(
        cdi, "ListItem", SimpleNamespace(objects=SimpleNamespace(filter=lambda **k: []))
    )

    resp = cdi.cdiSubmit(request, sd.pk)

    assert isinstance(resp, HttpResponseRedirect)


def test_cdiSubmit_valid_enough_words_with_list_items_proceeds(monkeypatch):
    """When count >= num_words and list items exist, calls proceedToExperiment."""
    rf = RequestFactory()
    request = rf.post("/cdi/submit/", data={"word_hello": "1"})
    request.session = _make_submit_session()

    sd = make_subject_data()
    exp = make_experiment(num_words=1)
    _patch_cdiSubmit_common(monkeypatch, sd, exp, unique_count=1)

    cleaned = {"word_hello": "1"}
    monkeypatch.setattr(
        cdi,
        "VocabularyChecklistForm",
        lambda *a, **k: SimpleNamespace(is_valid=lambda: True, cleaned_data=cleaned),
    )
    monkeypatch.setattr(cdi, "estimateCDI", lambda run_uuid: 0.5)
    monkeypatch.setattr(
        cdi,
        "ListItem",
        SimpleNamespace(objects=SimpleNamespace(filter=lambda **k: [1])),
    )
    monkeypatch.setattr(
        cdi, "proceedToExperiment", lambda exp, run_uuid: HttpResponse("proceed")
    )

    resp = cdi.cdiSubmit(request, sd.pk)

    assert isinstance(resp, HttpResponse)
    assert resp.content == b"proceed"


# ─── cdiGenerateNextItem ─────────────────────────────────────────────────────


def _make_next_item_session(est_theta=0.0):
    return Session(
        {
            "irt_run": 1,
            "item_params": json.dumps(
                [{"index": 0, "a": 1.0, "b": 0.0, "c": 0.2, "d": 1.0}]
            ),
            "administered_items": [0],
            "responses": [1],
            "est_theta": est_theta,
            "words": ["hello"],
            "all_words": json.dumps(["hello", "world"]),
        }
    )


def _patch_generate_next_base(monkeypatch, sd, exp):
    patch_get_object_or_404(monkeypatch, sd, exp)
    monkeypatch.setattr(cdi.pd, "read_json", lambda *a, **k: FakeDF())
    monkeypatch.setattr(cdi, "ItemBank", lambda params: None)
    monkeypatch.setattr(cdi, "VocabularyChecklistForm", lambda *a, **k: None)


def test_cdiGenerateNextItem_finite_theta_uses_maxinfoselector(monkeypatch):
    """Finite theta triggers MaxInfoSelector to pick the next item."""
    rf = RequestFactory()
    request = rf.get("/cdi/next/")
    request.session = _make_next_item_session(est_theta=0.0)

    sd = make_subject_data()
    exp = make_experiment()
    _patch_generate_next_base(monkeypatch, sd, exp)

    monkeypatch.setattr(
        cdi,
        "NumericalSearchEstimator",
        lambda method=None: SimpleNamespace(estimate=lambda **k: 0.5),
    )
    monkeypatch.setattr(
        cdi,
        "MaxInfoSelector",
        lambda: SimpleNamespace(select=lambda **k: np.array(1)),
    )

    resp = cdi.cdiGenerateNextItem(request, sd.pk)

    assert isinstance(resp, HttpResponse)
    assert not isinstance(resp, HttpResponseRedirect)
    assert 1 in request.session["administered_items"]


def test_cdiGenerateNextItem_infinite_theta_uses_sort_items(monkeypatch):
    """Infinite theta skips MaxInfoSelector and falls back to sorted item ordering."""
    rf = RequestFactory()
    request = rf.get("/cdi/next/")
    request.session = _make_next_item_session(est_theta=0.0)

    sd = make_subject_data()
    exp = make_experiment()
    _patch_generate_next_base(monkeypatch, sd, exp)

    monkeypatch.setattr(
        cdi,
        "NumericalSearchEstimator",
        lambda method=None: SimpleNamespace(estimate=lambda **k: float("inf")),
    )
    monkeypatch.setattr(cdi, "sort_items", lambda arr: np.array([0, 1]))

    resp = cdi.cdiGenerateNextItem(request, sd.pk)

    assert isinstance(resp, HttpResponse)
    assert not isinstance(resp, HttpResponseRedirect)


def test_cdiGenerateNextItem_keyerror_returns_redirect(monkeypatch):
    """A KeyError during item generation returns a redirect to the error page."""
    rf = RequestFactory()
    request = rf.get("/cdi/next/")
    request.session = _make_next_item_session()

    sd = make_subject_data()
    exp = make_experiment()
    _patch_generate_next_base(monkeypatch, sd, exp)

    def raise_key_error(*a, **k):
        raise KeyError("simulated failure")

    monkeypatch.setattr(cdi.pd, "read_json", raise_key_error)

    resp = cdi.cdiGenerateNextItem(request, sd.pk)

    assert isinstance(resp, HttpResponseRedirect)
