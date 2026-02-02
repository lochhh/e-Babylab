from django.urls import reverse, resolve
import pytest


def test_index_url_resolves():
    url = reverse("experiments:index")
    assert url.endswith("/")


def test_experiment_information_page_url_pattern():
    # the information page url requires an id; ensure reverse builds a path for a sample UUID
    path = reverse("experiments:informationPage", args=("00000000-0000-0000-0000-000000000000",))
    assert "information" in path or path.endswith("/")
