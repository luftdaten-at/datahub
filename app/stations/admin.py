from django.contrib import admin

from .models import FavoriteStation


@admin.register(FavoriteStation)
class FavoriteStationAdmin(admin.ModelAdmin):
    list_display = ("user", "station_id", "created_at")
    list_filter = ("created_at",)
    search_fields = ("station_id", "user__username")
    raw_id_fields = ("user",)
