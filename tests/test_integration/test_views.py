"""
Integration tests for experiments views (index and detail).
"""
from django.urls import reverse
import pytest

@pytest.mark.django_db
def test_index_no_questions(client):
    url = reverse("experiments:subjectForm", args=("00000000-0000-0000-0000-000000000000",))
    response = client.get(url)
    assert response.status_code == 200
    assert "latest_question_list" in response.context
    assert list(response.context["latest_question_list"]) == []


def test_index_with_question_shown(client, question_factory, experiment_factory):
    ex = experiment_factory()
    q = question_factory(text="Displayed question", position=1, experiment=ex)
    resp = client.get(reverse("experiments:subjectForm", args=(ex.id,)))
    assert resp.status_code == 200
    assert any("Displayed question" in str(x) for x in resp.context.get("latest_question_list", []))

@pytest.mark.django_db
def test_information_page_nonexistent_returns_404(client):
    resp = client.get(reverse("experiments:informationPage", args=("00000000-0000-0000-0000-000000000000",)))
    assert resp.status_code == 404
