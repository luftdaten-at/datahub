"""main URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import JavaScriptCatalog

from accounts.views import DashboardView

urlpatterns = [
    path('campaign/admin/jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),  # Add this line
    # Django admin
    path('backend/', admin.site.urls),
    # User management
    path('accounts/', include('accounts.urls')),
    path('dashboard/', DashboardView, name='dashboard'),
    # Local apps
    path('', include('pages.urls')),
    path('api/', include('api.urls')),
    path('campaigns/', include('campaign.urls')),
    path('cities/', include('cities.urls')),
    path('devices/', include('devices.urls')),
    path('stations/', include('stations.urls')),
    path('workshops/', include('workshops.urls')),
    path('organizations/', include('organizations.urls')),
] + i18n_patterns(
    # Your URLs that require localization
    # Include set_language URL
    path('i18n/', include('django.conf.urls.i18n')),
)