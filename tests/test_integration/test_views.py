"""
Integration tests for experiments views (index and detail).
"""
from django.urls import reverse
import pytest

@pytest.mark.django_db
def test_index_no_questions(client, experiment_factory):
    ex = experiment_factory()
    url = reverse("experiments:subjectForm", args=(ex.id,))
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_index_with_question_shown(client, question_factory, experiment_factory):
    ex = experiment_factory()
    question_factory(text="Displayed question", position=1, experiment=ex)
    resp = client.get(reverse("experiments:subjectForm", args=(ex.id,)))
    assert resp.status_code == 200
    assert b"Displayed question" in resp.content

@pytest.mark.django_db
def test_information_page_nonexistent_returns_404(client):
    resp = client.get(reverse("experiments:informationPage", args=("00000000-0000-0000-0000-000000000000",)))
    assert resp.status_code == 404
