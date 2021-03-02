from django import forms
from django.forms import models
from .models import Question, Experiment, SubjectData, AnswerInteger, AnswerRadio, AnswerSelect, AnswerSelectMultiple, AnswerText
from django.utils.safestring import mark_safe
from django.db.models import Max
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ValidationError

import uuid

class ConsentForm(forms.Form):
	"""
	Generates list of Y/N questions for the consent form.
	"""
	def __init__(self, *args, **kwargs):
		experiment = kwargs.pop('experiment')
		super(ConsentForm, self).__init__(*args, **kwargs)

		data = kwargs.get('data')
		for q in experiment.consent_questions():
			self.fields["question_%d" % q.pk] = forms.ChoiceField(label=q.text, widget=forms.RadioSelect, choices=(
                [('yes', q.response_yes), ('no', q.response_no),]),)
			self.fields["question_%d" % q.pk].widget.attrs["class"] = "required list-unstyled"
			
class SubjectDataForm(models.ModelForm):
	"""
	Generates the questions and answer fields for the demographic/participant data form.
	"""
	class Meta:
		model = SubjectData
		fields = ('resolution_w', 'resolution_h')
		widgets = {
            'resolution_w': forms.HiddenInput(),
            'resolution_h': forms.HiddenInput()
        }
	
	def __init__(self, *args, **kwargs):
		# expects an experiment object to be passed in initially
		experiment = kwargs.pop('experiment')
		self.experiment = experiment
		super(SubjectDataForm, self).__init__(*args, **kwargs)
		self.uuid = random_uuid = uuid.uuid4().hex

		# add a field for each question, corresponding to the question
		# type as appropriate.
		data = kwargs.get('data')
		for q in experiment.subject_questions():
			if q.question_type == Question.TEXT:
				self.fields["question_%d" % q.pk] = forms.CharField(label=q.text, widget=forms.Textarea(attrs={'rows': 1}))
			elif q.question_type == Question.RADIO:
				question_choices = q.get_choices()
				self.fields["question_%d" % q.pk] = forms.ChoiceField(label=q.text, widget=forms.RadioSelect, choices=question_choices)
			elif q.question_type == Question.SELECT:
				question_choices = q.get_choices()
				# add an empty option at the top so that the user has to
				# explicitly select one of the options
				question_choices = tuple([('', '-------------')]) + question_choices
				self.fields["question_%d" % q.pk] = forms.ChoiceField(label=q.text, widget=forms.Select, choices = question_choices)
			elif q.question_type == Question.SELECT_MULTIPLE:
				question_choices = q.get_choices()
				self.fields["question_%d" % q.pk] = forms.MultipleChoiceField(label=q.text, widget=forms.CheckboxSelectMultiple, choices = question_choices)
			elif q.question_type == Question.INTEGER:
				self.fields["question_%d" % q.pk] = forms.IntegerField(label=q.text)

			# if the required, give it a corresponding css class.
			if q.required:
				self.fields["question_%d" % q.pk].required = True
				self.fields["question_%d" % q.pk].widget.attrs["class"] = "required list-unstyled"
			else:
				self.fields["question_%d" % q.pk].required = False
				self.fields["question_%d" % q.pk].widget.attrs["class"] = "list-unstyled"
			
			# initialise the form filed with values from a POST request, if any.
			if data:
				self.fields["question_%d" % q.pk].initial = data.get('question_%d' % q.pk)
		
	def save(self, commit=True):
		"""
		Save the SubjectData object
		"""
		subjectData = super(SubjectDataForm, self).save(commit=False)
		subjectData.experiment = self.experiment
		subjectData.id = self.uuid
		if SubjectData.objects.filter(experiment=self.experiment.pk): 
			# get largest participant number
			subjectData.participant_id = SubjectData.objects.filter(experiment=self.experiment.pk).aggregate(Max('participant_id'))['participant_id__max'] + 1
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

				if q.question_type == Question.TEXT:
					a = AnswerText(question = q)
					a.body = field_value
				elif q.question_type == Question.RADIO:
					a = AnswerRadio(question = q)
					a.body = field_value
				elif q.question_type == Question.SELECT:
					a = AnswerSelect(question = q)
					a.body = field_value
				elif q.question_type == Question.SELECT_MULTIPLE:
					a = AnswerSelectMultiple(question = q)
					a.body = field_value
				elif q.question_type == Question.INTEGER:
					a = AnswerInteger(question = q)
					a.body = field_value
				print("creating answer to question %d of type %s" % (q_id, a.question.question_type))
				print(a.question.text)
				print("answer value: ")
				print(field_value)
				a.subject_data = subjectData
				a.save()
		return subjectData

class ExperimentForm(forms.ModelForm):
	"""
	Provides the multi-select fields containing a list of all existing groups.
	"""
	class Meta:
		model = Experiment
		fields = '__all__'
		
	sharing_groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False, widget=FilteredSelectMultiple("groups", is_stacked=False))
    
	def clean_sharing_groups(self):
		"""
		Checks that at least one group is selected when experiment is to be shared with groups.
		"""
		sharing_option = self.cleaned_data.get('sharing_option')
		groups = self.cleaned_data.get('sharing_groups')
		
		if sharing_option == 'GRP':
			if not groups:
				raise ValidationError('Please select at least one group.')
		return groups

class ImportForm(forms.Form):
	"""
	Provides the form for JSON file upload when an experiment is to be imported.
	"""
	import_file = forms.FileField(label='JSON File')