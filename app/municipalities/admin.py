from django.contrib import admin

from .models import FavoriteMunicipality


@admin.register(FavoriteMunicipality)
class FavoriteMunicipalityAdmin(admin.ModelAdmin):
    list_display = ("user", "municipality_slug", "created_at")
    list_filter = ("created_at",)
    search_fields = ("municipality_slug", "user__username")
    raw_id_fields = ("user",)
