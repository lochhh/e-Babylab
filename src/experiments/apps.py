"""Experiments app metadata and configuration."""

from django.apps import AppConfig


class ExperimentsConfig(AppConfig):
    """Django app config for the experiments app."""

    name = "experiments"

    def ready(self):
        """Patch filer's file_icon_url to strip erroneous escapejs from the icon URL.

        Django's escapejs converts '-' to r'-'; browsers then treat the backslash
        as a path separator, producing 'file/u002Dunknown.svg' (404) instead of
        'file-unknown.svg'. The URL is in a data-* HTML attribute, not inline JS,
        so no JavaScript escaping is needed.
        """
        from filer.settings import FILER_TABLE_ICON_SIZE
        from filer.templatetags import filer_admin_tags as _filer_tags

        def file_icon_url(file):
            if not hasattr(file, "_file_icon_url_safe_cache"):
                context = _filer_tags.file_icon_context(
                    file, False, 2 * FILER_TABLE_ICON_SIZE, 2 * FILER_TABLE_ICON_SIZE
                )
                file._file_icon_url_safe_cache = context.get(
                    "highres_url", context["icon_url"]
                )
            return file._file_icon_url_safe_cache

        _filer_tags.register.simple_tag(file_icon_url)
