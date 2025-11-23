from django.urls import reverse, resolve
import pytest


def test_index_url_resolves():
    url = reverse("experiments:index")
    assert url.endswith("/")


def test_detail_url_pattern():
    # the detail url requires an id; ensure reverse builds a path for a sample UUID
    path = reverse("experiments:detail", args=("00000000-0000-0000-0000-000000000000",))
    assert "detail" in path or path.endswith("/")
