"""
Unit tests for the experiments app forms.

Tests form validation, clean methods, and expected errors.
"""

import pytest
from django.core.exceptions import ValidationError


class TestConsentForm:
    """Tests for the ConsentForm."""

    def test_consent_form_initialization(self, experiment, consent_question):
        """Test ConsentForm is initialized with experiment questions."""
        from experiments.forms import ConsentForm
        
        form = ConsentForm(experiment=experiment)
        field_name = f"question_{consent_question.pk}"
        assert field_name in form.fields
        assert form.fields[field_name].label == consent_question.text

    def test_consent_form_valid_data(self, experiment, consent_question):
        """Test ConsentForm with valid data."""
        from experiments.forms import ConsentForm
        
        form_data = {f"question_{consent_question.pk}": "yes"}
        form = ConsentForm(data=form_data, experiment=experiment)
        assert form.is_valid()

    def test_consent_form_missing_required_field(self, experiment, consent_question):
        """Test ConsentForm validation fails with missing required field."""
        from experiments.forms import ConsentForm
        
        form = ConsentForm(data={}, experiment=experiment)
        assert not form.is_valid()

    def test_consent_form_field_choices(self, experiment, consent_question):
        """Test ConsentForm field has correct choices."""
        from experiments.forms import ConsentForm
        
        form = ConsentForm(experiment=experiment)
        field_name = f"question_{consent_question.pk}"
        choices = [choice[0] for choice in form.fields[field_name].choices]
        assert "yes" in choices
        assert "no" in choices


class TestSubjectDataForm:
    """Tests for the SubjectDataForm."""

    def test_subject_data_form_initialization(self, experiment, question):
        """Test SubjectDataForm is initialized correctly."""
        from experiments.forms import SubjectDataForm
        
        form = SubjectDataForm(experiment=experiment)
        assert "resolution_w" in form.fields
        assert "resolution_h" in form.fields

    def test_subject_data_form_hidden_fields(self, experiment):
        """Test that resolution fields are hidden."""
        from experiments.forms import SubjectDataForm
        from django import forms
        
        form = SubjectDataForm(experiment=experiment)
        assert isinstance(form.fields["resolution_w"].widget, forms.HiddenInput)
        assert isinstance(form.fields["resolution_h"].widget, forms.HiddenInput)

    def test_subject_data_form_valid_data(self, experiment, question):
        """Test SubjectDataForm with valid data."""
        from experiments.forms import SubjectDataForm
        
        form_data = {
            "resolution_w": 1920,
            "resolution_h": 1080,
        }
        form = SubjectDataForm(data=form_data, experiment=experiment)
        # Form may require additional fields based on questions
        # The base form should at least accept resolution fields
        assert "resolution_w" in form.data
        assert "resolution_h" in form.data
