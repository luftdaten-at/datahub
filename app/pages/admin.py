from django.contrib import admin
from django.contrib.sites.models import Site

# Unregister the Site model from admin
admin.site.unregister(Site)