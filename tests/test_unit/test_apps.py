"""Tests for ExperimentsConfig.ready() filer patch."""

from unittest.mock import patch

import pytest
from django.template import Context, Template
from filer.settings import FILER_TABLE_ICON_SIZE


class FakeFile:
    """Minimal file-like object that accepts arbitrary attribute assignment."""


@pytest.fixture
def fake_file():
    """Return a fresh FakeFile with no attributes set."""
    return FakeFile()


def _call_tag(file_obj):
    """Render the file_icon_url simple tag and return its string output."""
    t = Template("{% load filer_admin_tags %}{% file_icon_url myfile %}")
    return t.render(Context({"myfile": file_obj}))


class TestFileIconUrlPatch:
    """Tests for the file_icon_url tag registered by ExperimentsConfig.ready()."""

    def test_returns_highres_url_when_present(self, fake_file):
        """Tag returns highres_url when file_icon_context provides one."""
        with patch("filer.templatetags.filer_admin_tags.file_icon_context") as mock_ctx:
            mock_ctx.return_value = {
                "highres_url": "/media/thumb@2x.png",
                "icon_url": "/static/filer/icons/file-unknown.svg",
            }
            result = _call_tag(fake_file)
        assert result == "/media/thumb@2x.png"

    def test_falls_back_to_icon_url_when_no_highres(self, fake_file):
        """Tag falls back to icon_url when highres_url is absent from context."""
        with patch("filer.templatetags.filer_admin_tags.file_icon_context") as mock_ctx:
            mock_ctx.return_value = {"icon_url": "/static/filer/icons/file-unknown.svg"}
            result = _call_tag(fake_file)
        assert result == "/static/filer/icons/file-unknown.svg"

    def test_hyphen_not_escapejs_escaped(self, fake_file):
        r"""Hyphens must appear as raw '-', not as escapejs-encoded '-'."""
        with patch("filer.templatetags.filer_admin_tags.file_icon_context") as mock_ctx:
            mock_ctx.return_value = {"icon_url": "/static/filer/icons/file-unknown.svg"}
            result = _call_tag(fake_file)
        assert "-" in result
        assert "\\u002D" not in result

    def test_file_icon_context_called_with_double_table_icon_size(self, fake_file):
        """Tag passes 2x FILER_TABLE_ICON_SIZE as width and height."""
        expected_size = 2 * FILER_TABLE_ICON_SIZE
        with patch("filer.templatetags.filer_admin_tags.file_icon_context") as mock_ctx:
            mock_ctx.return_value = {"icon_url": "/static/icon.svg"}
            _call_tag(fake_file)
        mock_ctx.assert_called_once_with(fake_file, False, expected_size, expected_size)

    def test_result_cached_on_file_object(self, fake_file):
        """Second call with same file object skips file_icon_context entirely."""
        with patch("filer.templatetags.filer_admin_tags.file_icon_context") as mock_ctx:
            mock_ctx.return_value = {"icon_url": "/static/icon.svg"}
            _call_tag(fake_file)
            _call_tag(fake_file)
        mock_ctx.assert_called_once()

    def test_cache_attribute_set_on_file_object(self, fake_file):
        """Resolved URL is stored on the file object as _file_icon_url_safe_cache."""
        with patch("filer.templatetags.filer_admin_tags.file_icon_context") as mock_ctx:
            mock_ctx.return_value = {"icon_url": "/static/icon.svg"}
            _call_tag(fake_file)
        assert fake_file._file_icon_url_safe_cache == "/static/icon.svg"
