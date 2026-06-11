"""Generated with the customdashboard management command.

This file contains the class for the main dashboard.

To activate your index dashboard add the following to your settings.py::
    GRAPPELLI_INDEX_DASHBOARD = 'app.dashboard.CustomIndexDashboard'
"""

from django.utils.translation import gettext_lazy as _
from grappelli.dashboard import Dashboard, modules


class CustomIndexDashboard(Dashboard):
    """Custom index dashboard for www."""

    def init_with_context(self, context):
        """Populate the dashboard with modules."""
        # append a recent actions module
        self.children.append(
            modules.RecentActions(
                _("Recent Actions"),
                limit=10,
                collapsible=False,
                column=2,
            )
        )

        # only list the django.contrib apps
        self.children.append(
            modules.ModelList(
                title="Authentication and Authorisation",
                collapsible=False,
                column=1,
                models=("django.contrib.*",),
            )
        )

        # list all models except for django.contrib, filer, and easy_thumbnails
        self.children.append(
            modules.ModelList(
                title="Experiments",
                collapsible=False,
                column=1,
                exclude=(
                    "django.contrib.*",
                    "filer.*",
                    "easy_thumbnails.*",
                ),
            )
        )

        # filer file/image management
        self.children.append(
            modules.ModelList(
                title="Media Management",
                collapsible=False,
                column=1,
                models=("filer.*",),
                exclude=("filer.models.thumbnailoptionmodels.*",),
            )
        )
