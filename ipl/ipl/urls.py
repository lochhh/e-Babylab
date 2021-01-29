"""ipl URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from filebrowser.sites import site
from django.urls import path

admin.autodiscover()

urlpatterns = [
    url(r'^', include('experiments.urls')),
    #url(r'^experiments/', include('experiments.urls')),
    path('grappelli/', include('grappelli.urls')),
    path('admin/filebrowser/', site.urls),
    path('admin/', admin.site.urls),
]

#admin.site.site_header = "Experiments Administration"
#admin.site.site_title = "e-Babylab"

# Webcam tests
urlpatterns += static(settings.WEBCAM_TEST_URL, document_root=settings.WEBCAM_TEST_ROOT)

# Reports
urlpatterns += static(settings.REPORTS_URL, document_root=settings.REPORTS_ROOT)

# Webcam uploads
@login_required
def protected_serve(request, path, document_root=None, show_indexes=False):
    return serve(request, path, document_root, show_indexes)

urlpatterns += static(settings.WEBCAM_URL, protected_serve, document_root=settings.WEBCAM_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)