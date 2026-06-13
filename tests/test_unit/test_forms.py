"""Unit tests for experiments/forms.py.

Covers: ConsentForm, SubjectDataForm (init, clean, save),
        QuestionInlineFormSet, ExperimentForm, VocabularyChecklistForm, ImportForm.
"""

import datetime

import pytest
from django import forms as django_forms

from experiments import forms as exp_forms
from experiments import models as exp_models

# ---------------------------------------------------------------------------
# ConsentForm
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConsentForm:
    """Tests for the ConsentForm class."""

    def test_no_consent_questions_produces_empty_form(self, experiment_factory):
        """Verify an experiment with no consent questions produces an empty form."""
        experiment = experiment_factory()
        form = exp_forms.ConsentForm(experiment=experiment)
        assert len(form.fields) == 0

    def test_one_consent_question_adds_one_choice_field(
        self, experiment_factory, consent_question_factory
    ):
        """Verify a single consent question adds one ChoiceField to the form."""
        experiment = experiment_factory()
        cq = consent_question_factory(text="I agree", experiment=experiment)
        form = exp_forms.ConsentForm(experiment=experiment)
        key = "question_%d" % cq.pk
        assert key in form.fields
        field = form.fields[key]
        assert isinstance(field, django_forms.ChoiceField)
        assert field.label == "I agree"

    def test_consent_field_choices_use_response_yes_no(
        self, experiment_factory, consent_question_factory
    ):
        """Verify the yes/no choices map to the question's response labels."""
        experiment = experiment_factory()
        cq = consent_question_factory(experiment=experiment)
        form = exp_forms.ConsentForm(experiment=experiment)
        key = "question_%d" % cq.pk
        choices = dict(form.fields[key].choices)
        assert "yes" in choices
        assert "no" in choices
        assert choices["yes"] == cq.response_yes
        assert choices["no"] == cq.response_no

    def test_consent_field_has_required_css_class(
        self, experiment_factory, consent_question_factory
    ):
        """Verify the consent field widget carries the required CSS class."""
        experiment = experiment_factory()
        cq = consent_question_factory(experiment=experiment)
        form = exp_forms.ConsentForm(experiment=experiment)
        key = "question_%d" % cq.pk
        assert "required" in form.fields[key].widget.attrs.get("class", "")

    def test_multiple_consent_questions_all_added(
        self, experiment_factory, consent_question_factory
    ):
        """Verify all consent questions are added as fields."""
        experiment = experiment_factory()
        cq1 = consent_question_factory(text="Q1", experiment=experiment, position=1)
        cq2 = consent_question_factory(text="Q2", experiment=experiment, position=2)
        form = exp_forms.ConsentForm(experiment=experiment)
        assert "question_%d" % cq1.pk in form.fields
        assert "question_%d" % cq2.pk in form.fields


# ---------------------------------------------------------------------------
# SubjectDataForm – __init__
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSubjectDataFormInit:
    """Tests for SubjectDataForm field generation from experiment questions."""

    def test_text_question_adds_char_field(self, experiment_factory, question_factory):
        """Verify a TEXT question adds a CharField to the form."""
        experiment = experiment_factory()
        q = question_factory(
            text="Name", experiment=experiment, question_type=exp_models.Question.TEXT
        )
        form = exp_forms.SubjectDataForm(experiment=experiment)
        key = "question_%d" % q.pk
        assert isinstance(form.fields[key], django_forms.CharField)
        assert form.fields[key].label == "Name"

    def test_radio_question_adds_choice_field_with_radio_widget(
        self, experiment_factory, question_factory
    ):
        """Verify a RADIO question adds a ChoiceField with a RadioSelect widget."""
        experiment = experiment_factory()
        q = question_factory(
            text="Color",
            experiment=experiment,
            question_type=exp_models.Question.RADIO,
            choices="Red, Blue",
        )
        form = exp_forms.SubjectDataForm(experiment=experiment)
        key = "question_%d" % q.pk
        assert isinstance(form.fields[key], django_forms.ChoiceField)
        assert isinstance(form.fields[key].widget, django_forms.RadioSelect)

    def test_sex_question_adds_choice_field_with_radio_widget(
        self, experiment_factory, question_factory
    ):
        """Verify a SEX question adds a ChoiceField with a RadioSelect widget."""
        experiment = experiment_factory()
        q = question_factory(
            text="Sex",
            experiment=experiment,
            question_type=exp_models.Question.SEX,
            choices="Female, Male",
        )
        form = exp_forms.SubjectDataForm(experiment=experiment)
        key = "question_%d" % q.pk
        assert isinstance(form.fields[key], django_forms.ChoiceField)
        assert isinstance(form.fields[key].widget, django_forms.RadioSelect)

    def test_select_question_adds_choice_field_with_empty_first_option(
        self, experiment_factory, question_factory
    ):
        """Verify a SELECT question adds a ChoiceField with an empty first option."""
        experiment = experiment_factory()
        q = question_factory(
            text="Country",
            experiment=experiment,
            question_type=exp_models.Question.SELECT,
            choices="A, B",
        )
        form = exp_forms.SubjectDataForm(experiment=experiment)
        key = "question_%d" % q.pk
        assert isinstance(form.fields[key], django_forms.ChoiceField)
        assert isinstance(form.fields[key].widget, django_forms.Select)
        # First choice must be empty sentinel
        first_value, _ = form.fields[key].choices[0]
        assert first_value == ""

    def test_select_multiple_question_adds_multiple_choice_field(
        self, experiment_factory, question_factory
    ):
        """Verify a SELECT_MULTIPLE question adds a MultipleChoiceField."""
        experiment = experiment_factory()
        q = question_factory(
            text="Tags",
            experiment=experiment,
            question_type=exp_models.Question.SELECT_MULTIPLE,
            choices="X, Y, Z",
        )
        form = exp_forms.SubjectDataForm(experiment=experiment)
        key = "question_%d" % q.pk
        assert isinstance(form.fields[key], django_forms.MultipleChoiceField)
        assert isinstance(form.fields[key].widget, django_forms.CheckboxSelectMultiple)

    def test_integer_question_adds_integer_field(
        self, experiment_factory, question_factory
    ):
        """Verify an INTEGER question adds an IntegerField."""
        experiment = experiment_factory()
        q = question_factory(
            text="Count",
            experiment=experiment,
            question_type=exp_models.Question.INTEGER,
        )
        form = exp_forms.SubjectDataForm(experiment=experiment)
        key = "question_%d" % q.pk
        assert isinstance(form.fields[key], django_forms.IntegerField)

    def test_num_range_question_sets_min_max(
        self, experiment_factory, question_factory
    ):
        """Verify a NUM_RANGE question sets min_value, max_value, and step."""
        experiment = experiment_factory()
        q = question_factory(
            text="Score",
            experiment=experiment,
            question_type=exp_models.Question.NUM_RANGE,
            choices="1, 10",
        )
        form = exp_forms.SubjectDataForm(experiment=experiment)
        key = "question_%d" % q.pk
        field = form.fields[key]
        assert isinstance(field, django_forms.IntegerField)
        assert field.min_value == 1
        assert field.max_value == 10
        assert field.widget.attrs.get("step") == "1"

    def test_age_question_adds_date_field(self, experiment_factory, question_factory):
        """Verify an AGE question adds a DateField."""
        experiment = experiment_factory()
        q = question_factory(
            text="DOB",
            experiment=experiment,
            question_type=exp_models.Question.AGE,
            choices="6, 36",
        )
        form = exp_forms.SubjectDataForm(experiment=experiment)
        key = "question_%d" % q.pk
        assert isinstance(form.fields[key], django_forms.DateField)

    def test_required_question_sets_required_true_and_css(
        self, experiment_factory, question_factory
    ):
        """Verify required questions set required=True and a required CSS class."""
        experiment = experiment_factory()
        q = question_factory(
            text="Must",
            experiment=experiment,
            question_type=exp_models.Question.TEXT,
            required=True,
        )
        form = exp_forms.SubjectDataForm(experiment=experiment)
        key = "question_%d" % q.pk
        assert form.fields[key].required is True
        assert "required" in form.fields[key].widget.attrs.get("class", "")

    def test_optional_question_sets_required_false_and_css(
        self, experiment_factory, question_factory
    ):
        """Verify optional questions set required=False and list-unstyled CSS class."""
        experiment = experiment_factory()
        q = question_factory(
            text="Optional",
            experiment=experiment,
            question_type=exp_models.Question.TEXT,
            required=False,
        )
        form = exp_forms.SubjectDataForm(experiment=experiment)
        key = "question_%d" % q.pk
        assert form.fields[key].required is False
        assert "list-unstyled" in form.fields[key].widget.attrs.get("class", "")

    def test_initial_populated_from_post_data(
        self, experiment_factory, question_factory
    ):
        """Verify POST data pre-fills initial values for question fields."""
        experiment = experiment_factory()
        q = question_factory(
            text="Name", experiment=experiment, question_type=exp_models.Question.TEXT
        )
        post_data = {
            "question_%d" % q.pk: "Alice",
            "resolution_w": "1920",
            "resolution_h": "1080",
        }
        form = exp_forms.SubjectDataForm(data=post_data, experiment=experiment)
        key = "question_%d" % q.pk
        assert form.fields[key].initial == "Alice"

    def test_no_questions_produces_only_hidden_fields(self, experiment_factory):
        """Verify a form with no questions contains only hidden resolution fields."""
        experiment = experiment_factory()
        form = exp_forms.SubjectDataForm(experiment=experiment)
        # Only resolution_w and resolution_h from Meta
        assert set(form.fields.keys()) == {"resolution_w", "resolution_h"}


# ---------------------------------------------------------------------------
# SubjectDataForm – clean (age validation)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSubjectDataFormClean:
    """Tests for SubjectDataForm.clean() — age-range validation."""

    def _make_form_with_dob(self, experiment, question, dob_str):
        """Build a bound form with the given date of birth string."""
        key = "question_%d" % question.pk
        data = {key: dob_str, "resolution_w": "0", "resolution_h": "0"}
        return exp_forms.SubjectDataForm(data=data, experiment=experiment)

    def test_age_within_range_is_valid(self, experiment_factory, question_factory):
        """Verify a date of birth within the allowed age range passes validation."""
        experiment = experiment_factory()
        # age range 6–36 months; a 12-month-old should pass
        q = question_factory(
            text="DOB",
            experiment=experiment,
            question_type=exp_models.Question.AGE,
            choices="6, 36",
            required=True,
        )
        twelve_months_ago = datetime.date.today() - datetime.timedelta(days=365)
        dob_str = twelve_months_ago.strftime("%Y-%m-%d")
        form = self._make_form_with_dob(experiment, q, dob_str)
        assert form.is_valid(), form.errors

    def test_age_below_minimum_adds_error(self, experiment_factory, question_factory):
        """Verify a date of birth below the minimum age adds a validation error."""
        experiment = experiment_factory()
        q = question_factory(
            text="DOB",
            experiment=experiment,
            question_type=exp_models.Question.AGE,
            choices="12, 36",
            required=True,
        )
        # 3-month-old: below minimum of 12 months
        three_months_ago = datetime.date.today() - datetime.timedelta(days=90)
        dob_str = three_months_ago.strftime("%Y-%m-%d")
        form = self._make_form_with_dob(experiment, q, dob_str)
        assert not form.is_valid()
        key = "question_%d" % q.pk
        assert key in form.errors

    def test_clean_invalid_date_does_not_raise(
        self, experiment_factory, question_factory
    ):
        """Verify clean() exits early when Django rejects the date field value."""
        experiment = experiment_factory()
        q = question_factory(
            text="DOB",
            experiment=experiment,
            question_type=exp_models.Question.AGE,
            choices="6, 36",
            required=True,
        )
        data = {
            "question_%d" % q.pk: "not-a-date",
            "resolution_w": "0",
            "resolution_h": "0",
        }
        form = exp_forms.SubjectDataForm(data=data, experiment=experiment)
        assert not form.is_valid()
        assert "question_%d" % q.pk in form.errors

    def test_age_above_maximum_adds_error(self, experiment_factory, question_factory):
        """Verify a date of birth above the maximum age adds a validation error."""
        experiment = experiment_factory()
        q = question_factory(
            text="DOB",
            experiment=experiment,
            question_type=exp_models.Question.AGE,
            choices="6, 12",
            required=True,
        )
        # 24-month-old: above maximum of 12 months
        two_years_ago = datetime.date.today() - datetime.timedelta(days=730)
        dob_str = two_years_ago.strftime("%Y-%m-%d")
        form = self._make_form_with_dob(experiment, q, dob_str)
        assert not form.is_valid()
        key = "question_%d" % q.pk
        assert key in form.errors


# ---------------------------------------------------------------------------
# SubjectDataForm – save
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSubjectDataFormSave:
    """Tests for SubjectDataForm.save() — SubjectData and Answer record creation."""

    def test_save_creates_subject_data_with_experiment_and_uuid(
        self, experiment_factory, question_factory
    ):
        """Verify save() creates a SubjectData with participant_id=1."""
        experiment = experiment_factory()
        q = question_factory(
            text="Name",
            experiment=experiment,
            question_type=exp_models.Question.TEXT,
            required=True,
        )
        key = "question_%d" % q.pk
        data = {key: "Alice", "resolution_w": "1920", "resolution_h": "1080"}
        form = exp_forms.SubjectDataForm(data=data, experiment=experiment)
        assert form.is_valid(), form.errors
        subject = form.save()
        assert subject.experiment == experiment
        assert subject.participant_id == 1
        assert subject.pk is not None

    def test_save_creates_answer_for_text_question(
        self, experiment_factory, question_factory
    ):
        """Verify save() creates an AnswerText record for a TEXT question."""
        experiment = experiment_factory()
        q = question_factory(
            text="Name",
            experiment=experiment,
            question_type=exp_models.Question.TEXT,
            required=True,
        )
        key = "question_%d" % q.pk
        data = {key: "Bob", "resolution_w": "0", "resolution_h": "0"}
        form = exp_forms.SubjectDataForm(data=data, experiment=experiment)
        assert form.is_valid(), form.errors
        subject = form.save()
        answer = exp_models.AnswerText.objects.get(subject_data=subject, question=q)
        assert answer.body == "Bob"

    def test_save_increments_participant_id(
        self, experiment_factory, question_factory, subjectdata_factory
    ):
        """Verify save() assigns participant_id as max existing + 1."""
        experiment = experiment_factory()
        # Pre-existing participant
        subjectdata_factory(experiment=experiment, participant_id=5)
        q = question_factory(
            text="Name",
            experiment=experiment,
            question_type=exp_models.Question.TEXT,
            required=True,
        )
        key = "question_%d" % q.pk
        data = {key: "Carol", "resolution_w": "0", "resolution_h": "0"}
        form = exp_forms.SubjectDataForm(data=data, experiment=experiment)
        assert form.is_valid(), form.errors
        subject = form.save()
        assert subject.participant_id == 6

    def test_save_creates_answer_for_integer_question(
        self, experiment_factory, question_factory
    ):
        """Verify save() creates an AnswerInteger record for an INTEGER question."""
        experiment = experiment_factory()
        q = question_factory(
            text="Age",
            experiment=experiment,
            question_type=exp_models.Question.INTEGER,
            required=True,
        )
        key = "question_%d" % q.pk
        data = {key: "7", "resolution_w": "0", "resolution_h": "0"}
        form = exp_forms.SubjectDataForm(data=data, experiment=experiment)
        assert form.is_valid(), form.errors
        subject = form.save()
        answer = exp_models.AnswerInteger.objects.get(subject_data=subject, question=q)
        assert answer.body == 7

    def test_save_creates_answer_for_radio_question(
        self, experiment_factory, question_factory
    ):
        """Verify save() creates an AnswerRadio record for a RADIO question."""
        experiment = experiment_factory()
        q = question_factory(
            text="Color",
            experiment=experiment,
            question_type=exp_models.Question.RADIO,
            choices="Red, Blue",
            required=True,
        )
        key = "question_%d" % q.pk
        data = {key: "Red", "resolution_w": "0", "resolution_h": "0"}
        form = exp_forms.SubjectDataForm(data=data, experiment=experiment)
        assert form.is_valid(), form.errors
        subject = form.save()
        answer = exp_models.AnswerRadio.objects.get(subject_data=subject, question=q)
        assert answer.body == "Red"

    def test_save_creates_answer_for_select_question(
        self, experiment_factory, question_factory
    ):
        """Verify save() creates an AnswerSelect record for a SELECT question."""
        experiment = experiment_factory()
        q = question_factory(
            text="Country",
            experiment=experiment,
            question_type=exp_models.Question.SELECT,
            choices="US, UK",
            required=True,
        )
        key = "question_%d" % q.pk
        data = {key: "US", "resolution_w": "0", "resolution_h": "0"}
        form = exp_forms.SubjectDataForm(data=data, experiment=experiment)
        assert form.is_valid(), form.errors
        subject = form.save()
        answer = exp_models.AnswerSelect.objects.get(subject_data=subject, question=q)
        assert answer.body == "US"

    def test_save_creates_answer_for_select_multiple_question(
        self, experiment_factory, question_factory
    ):
        """Verify save() stores an AnswerSelectMultiple for SELECT_MULTIPLE."""
        experiment = experiment_factory()
        q = question_factory(
            text="Langs",
            experiment=experiment,
            question_type=exp_models.Question.SELECT_MULTIPLE,
            choices="EN, FR, DE",
            required=True,
        )
        key = "question_%d" % q.pk
        data = {key: ["EN", "FR"], "resolution_w": "0", "resolution_h": "0"}
        form = exp_forms.SubjectDataForm(data=data, experiment=experiment)
        assert form.is_valid(), form.errors
        subject = form.save()
        answer = exp_models.AnswerSelectMultiple.objects.get(
            subject_data=subject, question=q
        )
        assert "EN" in answer.body


# ---------------------------------------------------------------------------
# QuestionInlineFormSet
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestQuestionInlineFormSet:
    """Tests for QuestionInlineFormSet default initial values."""

    def test_adds_default_initial_when_no_questions_exist(self, experiment_factory):
        """Verify age/sex questions are injected as initial data when none exist."""
        from experiments.forms import QuestionInlineFormSet
        from experiments.models import Question

        experiment = experiment_factory()
        QuestionFormSet = django_forms.inlineformset_factory(
            exp_models.Experiment,
            Question,
            formset=QuestionInlineFormSet,
            fields=["text", "question_type", "required", "choices"],
        )
        formset = QuestionFormSet(instance=experiment)
        initial_types = [
            f.initial.get("question_type") for f in formset.extra_forms if f.initial
        ]
        assert "age" in initial_types
        assert "sex" in initial_types

    def test_no_default_initial_when_questions_already_exist(
        self, experiment_factory, question_factory
    ):
        """Verify no initial data is injected when questions already exist."""
        from experiments.forms import QuestionInlineFormSet
        from experiments.models import Question

        experiment = experiment_factory()
        # Create a question to ensure the formset has an existing question
        expected_question = question_factory(
            experiment=experiment, text="Expected Question"
        )
        # Set extra=0 to match UI behaviour (admin.py),
        # where no blank forms are shown when questions already exist
        QuestionFormSet = django_forms.inlineformset_factory(
            exp_models.Experiment,
            Question,
            formset=QuestionInlineFormSet,
            fields=["text", "question_type", "required", "choices"],
            extra=0,
        )
        formset = QuestionFormSet(instance=experiment)
        assert len(formset.initial_forms) == 1
        assert formset.initial_forms[0].instance == expected_question


# ---------------------------------------------------------------------------
# ExperimentForm
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExperimentForm:
    """Tests for ExperimentForm — sharing_groups clean validation."""

    def _bound_form(self, sharing_option, groups):
        """Build a bound ExperimentForm with the given sharing_option and groups."""
        data = {
            "exp_name": "Test",
            "sharing_option": sharing_option,
            "sharing_groups": [g.pk for g in groups],
            "list_selection_strategy": "LPF",
            "recording_option": "NON",
            "general_onset": "0",
            "num_words": "25",
            "assess_type": "COMP",
            "include_pause_page": True,
            "show_gaze_estimations": False,
            "typical_dev": True,
        }
        return exp_forms.ExperimentForm(data=data)

    def test_clean_sharing_groups_raises_when_grp_and_no_groups(self, user):
        """Verify a validation error when GRP sharing is set with no groups selected."""
        form = self._bound_form("GRP", [])
        assert not form.is_valid()
        assert "sharing_groups" in form.errors

    def test_clean_sharing_groups_valid_when_grp_and_groups_provided(self, group):
        """Verify no sharing_groups error when groups are provided for GRP sharing."""
        form = self._bound_form("GRP", [group])
        # Other required fields may be missing; only check sharing_groups has no error.
        form.is_valid()
        assert "sharing_groups" not in form.errors

    def test_clean_sharing_groups_valid_when_private_and_no_groups(self, user):
        """Verify no sharing_groups error when sharing_option is OWN."""
        form = self._bound_form("OWN", [])
        form.is_valid()
        assert "sharing_groups" not in form.errors

    def test_clean_sharing_groups_valid_when_public_and_no_groups(self, user):
        """Verify no sharing_groups error when sharing_option is PUB."""
        form = self._bound_form("PUB", [])
        form.is_valid()
        assert "sharing_groups" not in form.errors


# ---------------------------------------------------------------------------
# VocabularyChecklistForm
# ---------------------------------------------------------------------------


class TestVocabularyChecklistForm:
    """Tests for VocabularyChecklistForm — word keyword argument behaviour."""

    def test_word_kwarg_adds_boolean_field(self):
        """Verify the word kwarg creates a BooleanField named word_<word>."""
        form = exp_forms.VocabularyChecklistForm(word="apple")
        assert "word_apple" in form.fields
        field = form.fields["word_apple"]
        assert isinstance(field, django_forms.BooleanField)
        assert field.label == "apple"
        assert field.required is False

    def test_word_field_has_list_unstyled_class(self):
        """Verify the word field has the list-unstyled CSS class."""
        form = exp_forms.VocabularyChecklistForm(word="banana")
        assert form.fields["word_banana"].widget.attrs.get("class") == "list-unstyled"

    def test_no_word_produces_empty_form(self):
        """Verify omitting the word kwarg produces a form with no fields."""
        form = exp_forms.VocabularyChecklistForm()
        assert len(form.fields) == 0

    def test_word_none_produces_empty_form(self):
        """Verify word=None produces a form with no fields."""
        form = exp_forms.VocabularyChecklistForm(word=None)
        assert len(form.fields) == 0

    def test_valid_with_word_checked(self):
        """Verify a checked word field is valid and returns True in cleaned_data."""
        form = exp_forms.VocabularyChecklistForm(data={"word_cat": True}, word="cat")
        assert form.is_valid()
        assert form.cleaned_data["word_cat"] is True

    def test_valid_with_word_unchecked(self):
        """Verify an unchecked word field is valid and returns False in cleaned_data."""
        # BooleanField with required=False: unchecked (absent from POST) should be valid
        form = exp_forms.VocabularyChecklistForm(data={}, word="cat")
        assert form.is_valid()
        assert form.cleaned_data["word_cat"] is False


# ---------------------------------------------------------------------------
# ImportForm
# ---------------------------------------------------------------------------


class TestImportForm:
    """Tests for ImportForm — file field presence and validation."""

    def test_import_form_has_file_field(self):
        """Verify the import form contains a FileField named import_file."""
        form = exp_forms.ImportForm()
        assert "import_file" in form.fields
        assert isinstance(form.fields["import_file"], django_forms.FileField)

    def test_import_form_invalid_without_file(self):
        """Verify the import form is invalid when no file is provided."""
        form = exp_forms.ImportForm(data={})
        assert not form.is_valid()
        assert "import_file" in form.errors
