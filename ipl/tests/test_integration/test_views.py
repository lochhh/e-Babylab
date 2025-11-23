"""
Integration tests for ipl.experiments views (index and detail).
"""
from django.urls import reverse
import pytest


def test_index_no_questions(client):
    url = reverse("experiments:index")
    response = client.get(url)
    assert response.status_code == 200
    assert b"No experiments are available." in response.content
    assert "latest_question_list" in response.context
    assert list(response.context["latest_question_list"]) == []


def test_index_with_question_shown(client, question_factory):
    q = question_factory(text="Displayed question", position=1)
    resp = client.get(reverse("experiments:index"))
    assert resp.status_code == 200
    assert any("Displayed question" in str(x) for x in resp.context.get("latest_question_list", []))


def test_detail_nonexistent_returns_404(client):
    resp = client.get(reverse("experiments:detail", args=("00000000-0000-0000-0000-000000000000",)))
    assert resp.status_code == 404
