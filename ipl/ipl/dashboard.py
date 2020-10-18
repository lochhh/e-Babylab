"""
This file was generated with the customdashboard management command and
contains the class for the main dashboard.

To activate your index dashboard add the following to your settings.py::
    GRAPPELLI_INDEX_DASHBOARD = 'app.dashboard.CustomIndexDashboard'
"""

from django.utils.translation import ugettext_lazy as _
from django.urls import reverse

from grappelli.dashboard import modules, Dashboard
from grappelli.dashboard.utils import get_admin_site_name


class CustomIndexDashboard(Dashboard):
    """
    Custom index dashboard for www.
    """

    def init_with_context(self, context):
        site_name = get_admin_site_name(context)

        # append a recent actions module
        self.children.append(modules.RecentActions(
            _('Recent Actions'),
            limit=10,
            collapsible=False,
            column=2,
        ))

        # will only list the django.contrib apps
        self.children.append(modules.ModelList(
            title='Authentication and Authorisation',
            collapsible=False,
            column=1,
            models=('django.contrib.*',)
        ))
        
        # will list all models except the django.contrib ones
        self.children.append(modules.ModelList(
            title='Experiments',
            collapsible=False,
            column=1,
            exclude=('django.contrib.*',)
        ))
        
        # link to file browser
        self.children.append(
            modules.LinkList(
                _('Media Management'),
                collapsible=False,
                column=1,
                children=[
                    {
                        'title': _('File Browser'),
                        'url': '/admin/filebrowser/browse/',
                        'external': False,
                    },
                ]))

