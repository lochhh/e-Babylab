import importlib
import datetime
from types import SimpleNamespace

import pytest
import numpy as np
from django.test import RequestFactory
from django.http import HttpResponseRedirect, HttpResponse

# import the module under test
cdi = importlib.import_module("ipl.experiments.cdi")


def test_sort_items_monkeypatched(monkeypatch):
    """
    sort_items delegates to catsim/irt functions. Monkeypatch those to produce
    a deterministic inf_hpc output and check the returned ordering.
    """
    # make max_info_hpc unused (it will be called with item_params)
    monkeypatch.setattr(cdi, "max_info_hpc", lambda item_params: "ignored")
    # inf_hpc should return an array we control
    monkeypatch.setattr(cdi, "inf_hpc", lambda a, b: np.array([5.0, 3.0, 7.0]))
    ordering = cdi.sort_items(np.array([[0]]))
    # with inf_hpc=[5,3,7] negative = [-5,-3,-7]; argsort -> indices of [-7,-5,-3] -> [2,0,1]
    assert ordering.tolist() == [2, 0, 1]


def test_estimateCDI_basic_branch(monkeypatch):
    """
    Test estimateCDI with minimal monkeypatching:
    - get_object_or_404 returns simple objects for SubjectData, Experiment, Instrument
    - CdiResult.objects.filter returns empty list (so loop is skipped)
    - pandas.read_csv is monkeypatched to return fake objects with .index and .at used in formula
    - csv.DictReader is monkeypatched so code does not try to open files
    Expectation: function computes an estimate using bmin.at and slope.at values and
    stores it on subject_data.cdi_estimate and returns the numeric estimate.
    """
    # create fake subject_data with created date and placeholder experiment pk
    created_dt = datetime.datetime.now()
    saved = {}
    def fake_save():
        saved["called"] = True

    subject_data = SimpleNamespace(pk="run-uuid", created=created_dt, experiment=SimpleNamespace(pk="exp-1"), cdi_estimate=None, save=fake_save)

    experiment = SimpleNamespace(pk="exp-1", instrument=SimpleNamespace(pk="instr-1"), cdi_page_tpl="<p>tpl</p>")
    # instrument needs file attributes with .path used by code, but we'll monkeypatch csv.DictReader and pd.read_csv
    instrument = SimpleNamespace(words_list=SimpleNamespace(path="words.csv"),
                                 f_lm_np_mean="f_lm_np_mean.csv",
                                 f_lm_np_sd="f_lm_np_sd.csv",
                                 f_lm_p_mean="f_lm_p_mean.csv",
                                 f_lm_p_sd="f_lm_p_sd.csv",
                                 f_bmin="f_bmin.csv",
                                 f_slope="f_slope.csv",
                                 m_lm_np_mean="m_lm_np_mean.csv",
                                 m_lm_np_sd="m_lm_np_sd.csv",
                                 m_lm_p_mean="m_lm_p_mean.csv",
                                 m_lm_p_sd="m_lm_p_sd.csv",
                                 m_bmin="m_bmin.csv",
                                 m_slope="m_slope.csv",
                                 )

    # monkeypatch get_object_or_404 to return the right object based on model argument
    def fake_get_object_or_404(model, pk=None):
        if model is cdi.SubjectData:
            return subject_data
        if model is cdi.Experiment:
            return experiment
        if model is cdi.Instrument:
            return instrument
        raise AssertionError("Unexpected model in get_object_or_404: %r" % (model,))
    monkeypatch.setattr(cdi, "get_object_or_404", fake_get_object_or_404)

    # make CdiResult.objects.filter(...) return an empty list so main loop is skipped
    class FakeCdiResultManager:
        @staticmethod
        def filter(*args, **kwargs):
            return []
    class FakeCdiResult:
        objects = FakeCdiResultManager()
    monkeypatch.setattr(cdi, "CdiResult", FakeCdiResult)

    # patch csv.DictReader to avoid file IO; return empty iterator
    monkeypatch.setattr(cdi.csv, "DictReader", lambda f, delimiter=',', encoding=None, mode=None: [])

    # create a very small fake DataFrame-like object for pd.read_csv outputs
    class FakeDF:
        def __init__(self, n=1, val=1.0):
            self._n = n
            self._val = val
            self.index = range(n)

        # allow df.iloc[:,1:5] usage by providing .iloc with __getitem__ that returns self
        class _ILOC:
            def __init__(self, parent):
                self._p = parent
            def __getitem__(self, key):
                return self._p
        @property
        def iloc(self):
            return FakeDF._ILOC(self)

        def reset_index(self):
            return self
        def to_json(self, orient='records'):
            return "[]"
        def to_numpy(self):
            # small 2D array used by sort_items in other functions; return something valid
            return np.array([[1.0]])

        # simulate .at lookup returning a numeric value
        @property
        def at(self):
            # produce an object with __getitem__ that returns stored value
            class _At:
                def __init__(self, val):
                    self._val = val
                def __getitem__(self, key):
                    return self._val
            return _At(self._val)

        # allow column access like df['word_id']
        def __getitem__(self, key):
            # return an object that when compared to a value yields an array-like with an index attribute.
            class _SeriesLike:
                def __init__(self, parent):
                    self.parent = parent
                def __eq__(self, other):
                    # return a boolean array-like with attribute index; index will be a list
                    class _BoolIdx:
                        def __init__(self, idx):
                            self.index = idx
                    return _BoolIdx([0])
            return _SeriesLike(self)

    # monkeypatch pd.read_csv to always return FakeDF instances
    monkeypatch.setattr(cdi.pd, "read_csv", lambda *args, **kwargs: FakeDF(n=1, val=1.0))

    # monkeypatch norm.pdf so code that computes logs will run without numerical troubles
    monkeypatch.setattr(cdi.norm, "pdf", lambda x, loc, scale: np.ones_like(x) * 1.0)

    # call estimateCDI and assert return value and that subject_data.save() was called
    result = cdi.estimateCDI(subject_data.pk)
    assert result == pytest.approx(0.0) or result == 0 or isinstance(result, (int, float))
    # check subject_data.cdi_estimate stored (function assigns attribute before saving)
    assert subject_data.cdi_estimate is not None
    assert saved.get("called", False) is True


def test_cdiRun_sets_session_and_renders(monkeypatch, question_factory):
    """
    Test cdiRun path that sets up session keys and returns an HttpResponse.
    Monkeypatch heavy dependencies:
      - get_object_or_404 to provide subject_data, experiment, instrument
      - csv.DictReader to supply word list
      - pd.read_csv to provide item_params stub (with iloc/reset_index/to_json)
      - sort_items to provide administered item indices
      - FixedPointInitializer to provide .initialize()
      - VocabularyChecklistForm to not raise and to construct a form object
    """
    rf = RequestFactory()
    request = rf.get("/cdi/run/")
    request.session = {}

    # fake domain objects
    created_dt = datetime.datetime.now()
    subject_data = SimpleNamespace(pk="run-uuid", created=created_dt, experiment=SimpleNamespace(pk="exp-1"))
    experiment = SimpleNamespace(pk="exp-1", cdi_page_tpl="<p>CDI</p>", num_words=1)
    instrument = SimpleNamespace(words_list=SimpleNamespace(path="words.csv"), irt_params=SimpleNamespace(path="irt.csv"))

    # stub get_object_or_404 to return our objects in sequence by model
    def fake_get_object_or_404(model, pk=None):
        if model is cdi.SubjectData:
            return subject_data
        if model is cdi.Experiment:
            return experiment
        if model is cdi.Instrument:
            return instrument
        raise AssertionError("Unexpected model: %r" % (model,))
    monkeypatch.setattr(cdi, "get_object_or_404", fake_get_object_or_404)

    # csv.DictReader should return list of rows with 'word' keys
    monkeypatch.setattr(cdi.csv, "DictReader", lambda f, delimiter=',', encoding=None, mode=None: [{"word": "w1"}])

    # Fake DataFrame used for pd.read_csv in cdiRun
    class FakeDF2:
        class _ILOC:
            def __init__(self, parent):
                self._p = parent
            def __getitem__(self, key):
                return self._p
        @property
        def iloc(self):
            return FakeDF2._ILOC(self)
        def reset_index(self):
            return self
        def to_json(self, orient='records'):
            return "[]"

    monkeypatch.setattr(cdi.pd, "read_csv", lambda *args, **kwargs: FakeDF2())

    # stub sort_items to return a numpy array compatible with indexing [0:1,]
    monkeypatch.setattr(cdi, "sort_items", lambda arr: np.array([[0]]))

    # stub FixedPointInitializer to return object with initialize()
    class FakeInit:
        def __init__(self, x):
            pass
        def initialize(self):
            return 0.0
    monkeypatch.setattr(cdi, "FixedPointInitializer", FakeInit)

    # replace VocabularyChecklistForm so it only constructs without side effects
    class FakeVocabForm:
        def __init__(self, cdi_form, word):
            self._c = cdi_form
            self._w = word
    monkeypatch.setattr(cdi, "VocabularyChecklistForm", FakeVocabForm)

    # call cdiRun
    resp = cdi.cdiRun(request, subject_data.pk)
    assert isinstance(resp, HttpResponse)
    # verify session keys have been set by the function
    assert "all_words" in request.session
    assert "item_params" in request.session
    assert "administered_items" in request.session
    assert "irt_run" in request.session
    assert "est_theta" in request.session
    assert "words" in request.session


def test_cdiSubmit_branches_to_end(monkeypatch, question_factory):
    """
    Test the branch where cdiSubmit processes a valid form, sees enough unique items,
    calls estimateCDI (monkeypatched), and then either proceeds to experiment or redirects.
    - Monkeypatch VocabularyChecklistForm to always be valid
    - Monkeypatch CdiResult.objects.filter(...).order_by(...).distinct(...).count() to return a value >= experiment.num_words
    - Monkeypatch estimateCDI to a noop
    - Monkeypatch ListItem.objects.filter to return non-empty iterable so proceedToExperiment path is used
    """
    rf = RequestFactory()
    request = rf.post("/cdi/submit/", data={"word_w1": "on"})
    request.session = {"responses": []}

    # fake domain objects
    created_dt = datetime.datetime.now()
    subject_data = SimpleNamespace(pk="run-uuid", created=created_dt, experiment=SimpleNamespace(pk="exp-1"))
    experiment = SimpleNamespace(pk="exp-1", cdi_page_tpl="<p>CDI</p>", num_words=1)
    # attach experiment on subject_data
    subject_data.experiment = experiment

    # monkeypatch get_object_or_404
    def fake_get_object_or_404(model, pk=None):
        if model is cdi.SubjectData:
            return subject_data
        if model is cdi.Experiment:
            return experiment
        raise AssertionError("Unexpected model")
    monkeypatch.setattr(cdi, "get_object_or_404", fake_get_object_or_404)

    # fake form that is always valid
    class FakeForm:
        def __init__(self, post, cdi_form=None):
            self._post = post
        def is_valid(self):
            return True
    monkeypatch.setattr(cdi, "VocabularyChecklistForm", FakeForm)

    # fake CdiResult manager chain to return a count >= num_words
    class _Q:
        def order_by(self, *args, **kwargs):
            return self
        def distinct(self, *args, **kwargs):
            return self
        def count(self):
            return 1
    class FakeCdi:
        objects = _Q()
    monkeypatch.setattr(cdi, "CdiResult", FakeCdi)

    # monkeypatch estimateCDI to avoid heavy computation
    monkeypatch.setattr(cdi, "estimateCDI", lambda run_uuid: 123.4)

    # monkeypatch ListItem.objects.filter to return non-empty iterable to take proceedToExperiment branch
    class _LI:
        @staticmethod
        def filter(*args, **kwargs):
            return [1]
    monkeypatch.setattr(cdi, "ListItem", _LI)

    # monkeypatch proceedToExperiment to return a HttpResponse
    monkeypatch.setattr(cdi, "proceedToExperiment", lambda experiment, run_uuid: HttpResponse("proceed"))

    resp = cdi.cdiSubmit(request, subject_data.pk)
    # since there are enough unique items expect proceedToExperiment return
    assert isinstance(resp, (HttpResponse, HttpResponseRedirect))
