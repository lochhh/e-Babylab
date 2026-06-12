"""Forms for participant data, consent, CDI, and experiment management."""

import datetime
import logging
import uuid

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.forms import models
from django.forms.widgets import DateInput

from .models import (
    AnswerInteger,
    AnswerRadio,
    AnswerSelect,
    AnswerSelectMultiple,
    AnswerText,
    Experiment,
    Question,
    SubjectData,
)

# Create a logger for this file
logger = logging.getLogger(__name__)


class ConsentForm(forms.Form):
    """Generates list of Y/N questions for the consent form."""

    def __init__(self, *args, **kwargs):
        """Build consent fields from the experiment's consent questions."""
        experiment = kwargs.pop("experiment")
        super().__init__(*args, **kwargs)

        for q in experiment.consent_questions():
            self.fields[f"question_{q.pk}"] = forms.ChoiceField(
                label=q.text,
                widget=forms.RadioSelect,
                choices=(
                    [
                        ("yes", q.response_yes),
                        ("no", q.response_no),
                    ]
                ),
            )
            self.fields[f"question_{q.pk}"].widget.attrs["class"] = (
                "required list-unstyled"
            )


class SubjectDataForm(models.ModelForm):
    """Generates the questions and answer fields for the participant data form."""

    class Meta:
        """Configure model and hidden resolution fields."""

        model = SubjectData
        fields = ("resolution_w", "resolution_h")
        widgets = {
            "resolution_w": forms.HiddenInput(),
            "resolution_h": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        """Build participant data fields from the experiment's subject questions."""
        # expects an experiment object to be passed in initially
        experiment = kwargs.pop("experiment")
        self.experiment = experiment
        super().__init__(*args, **kwargs)
        self.uuid = uuid.uuid4().hex

        # add a field for each question, corresponding to the question
        # type as appropriate.
        data = kwargs.get("data")
        for q in experiment.subject_questions():
            field_name = f"question_{q.pk}"
            if q.question_type == Question.TEXT:
                self.fields[field_name] = forms.CharField(
                    label=q.text, widget=forms.Textarea(attrs={"rows": 1})
                )
            elif q.question_type == Question.RADIO or q.question_type == Question.SEX:
                question_choices = q.get_choices()
                self.fields[field_name] = forms.ChoiceField(
                    label=q.text, widget=forms.RadioSelect, choices=question_choices
                )
            elif q.question_type == Question.SELECT:
                question_choices = q.get_choices()
                # add an empty option at the top so that the user has to
                # explicitly select one of the options
                question_choices = (("", "-------------"), *question_choices)
                self.fields[field_name] = forms.ChoiceField(
                    label=q.text, widget=forms.Select, choices=question_choices
                )
            elif q.question_type == Question.SELECT_MULTIPLE:
                question_choices = q.get_choices()
                self.fields[field_name] = forms.MultipleChoiceField(
                    label=q.text,
                    widget=forms.CheckboxSelectMultiple,
                    choices=question_choices,
                )
            elif q.question_type == Question.INTEGER:
                self.fields[field_name] = forms.IntegerField(
                    label=q.text, localize=True
                )
            elif q.question_type == Question.NUM_RANGE:
                question_choices = q.get_choices()
                self.fields[field_name] = forms.IntegerField(
                    label=q.text,
                    min_value=int(question_choices[0][0]),
                    max_value=int(question_choices[1][0]),
                    localize=True,
                )
                self.fields[field_name].widget.attrs["step"] = "1"
            elif q.question_type == Question.AGE:
                self.fields[field_name] = forms.DateField(
                    label=q.text,
                    initial=datetime.date.today,
                    widget=DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
                )
            # if the required, give it a corresponding css class.
            if q.required:
                self.fields[field_name].required = True
                self.fields[field_name].widget.attrs["class"] = "required list-unstyled"
            else:
                self.fields[field_name].required = False
                self.fields[field_name].widget.attrs["class"] = "list-unstyled"

            # initialise the form filed with values from a POST request, if any.
            if data:
                self.fields[field_name].initial = data.get(field_name)

    def clean(self):
        """Validate responses and compute participant age from any date fields."""
        cleaned_data = super().clean()

        # find datetime object
        for field_name, field_value in cleaned_data.items():
            if isinstance(field_value, datetime.date):
                # get age range
                age_question = Question.objects.filter(
                    experiment=self.experiment.pk, question_type="age"
                ).first()
                if age_question:
                    age_mo = ((datetime.date.today() - field_value).days) / (365 / 12)
                    age_range = age_question.get_choices()
                    min_age = int(age_range[0][0])
                    max_age = int(age_range[1][0])
                    if age_mo < min_age:
                        self.add_error(field_name, "Min: " + str(min_age) + " mo.")
                    if age_mo > max_age:
                        self.add_error(field_name, "Max: " + str(max_age) + " mo.")
                    logger.info("Age in months: " + str(round(age_mo)))
                    break
        return cleaned_data

    def save(self, commit=True):
        """Save the SubjectData object."""
        subjectData = super().save(commit=False)
        subjectData.experiment = self.experiment
        subjectData.id = self.uuid
        if SubjectData.objects.filter(experiment=self.experiment.pk):
            # get largest participant number
            subjectData.participant_id = (
                SubjectData.objects.filter(experiment=self.experiment.pk).aggregate(
                    Max("participant_id")
                )["participant_id__max"]
                + 1
            )
        else:
            # first participant
            subjectData.participant_id = 1
        subjectData.save()

        # create an answer object for each question and associate it with SubjectData.
        for field_name, field_value in self.cleaned_data.items():
            if field_name.startswith("question_"):
                # warning: this way of extracting the id is very fragile and
                # entirely dependent on the way the question_id is encoded in
                # the field name in the __init__ method of this form class.
                q_id = int(field_name.split("_")[1])
                q = Question.objects.get(pk=q_id)

                if q.question_type == Question.TEXT or q.question_type == Question.AGE:
                    a = AnswerText(question=q)
                    a.body = field_value
                elif (
                    q.question_type == Question.RADIO or q.question_type == Question.SEX
                ):
                    a = AnswerRadio(question=q)
                    a.body = field_value
                elif q.question_type == Question.SELECT:
                    a = AnswerSelect(question=q)
                    a.body = field_value
                elif q.question_type == Question.SELECT_MULTIPLE:
                    a = AnswerSelectMultiple(question=q)
                    a.body = field_value
                elif (
                    q.question_type == Question.INTEGER
                    or q.question_type == Question.NUM_RANGE
                ):
                    a = AnswerInteger(question=q)
                    a.body = field_value

                logger.info(
                    f'Creating answer to "{a.question.text}" '
                    f"(question {q_id}) of type "
                    f"{a.question.question_type}: {field_value}"
                )
                a.subject_data = subjectData
                a.save()
        return subjectData


class QuestionInlineFormSet(models.BaseInlineFormSet):
    """Formset for demographic questions that pre-populates default fields."""

    def __init__(self, *args, **kwargs):
        """Pre-populate age/sex fields when no questions exist yet."""
        experiment = kwargs.get("instance")
        if (
            experiment
            and not Question.objects.filter(experiment=experiment.pk).exists()
        ):
            kwargs.update(
                {
                    "initial": [
                        {
                            "text": "Date of birth",
                            "question_type": "age",
                            "required": True,
                        },
                        {
                            "text": "Sex",
                            "question_type": "sex",
                            "choices": "Female, Male",
                            "required": True,
                        },
                    ]
                }
            )
        super().__init__(*args, **kwargs)


class ExperimentForm(forms.ModelForm):
    """Provides the multi-select fields containing a list of all existing groups."""

    class Meta:
        """Configure model and include all fields."""

        model = Experiment
        fields = "__all__"

    sharing_groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=FilteredSelectMultiple("groups", is_stacked=False),
    )

    def clean_sharing_groups(self):
        """Check that at least one group is selected for group-shared experiments."""
        sharing_option = self.cleaned_data.get("sharing_option")
        groups = self.cleaned_data.get("sharing_groups")

        if sharing_option == "GRP" and not groups:
            raise ValidationError("Please select at least one group.")
        return groups


class VocabularyChecklistForm(forms.Form):
    """Generates the vocabulary checklist form."""

    def __init__(self, *args, **kwargs):
        """Build a single checkbox field for the given CDI word."""
        word = kwargs.pop("word", None)
        super().__init__(*args, **kwargs)

        if word:
            field_name = f"word_{word}"
            self.fields[field_name] = forms.BooleanField(
                label=word,
                required=False,
                widget=forms.CheckboxInput(attrs={"class": "list-unstyled"}),
            )


class ImportForm(forms.Form):
    """Provides the form for JSON file upload when an experiment is to be imported."""

    import_file = forms.FileField(label="JSON File")
