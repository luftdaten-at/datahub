from django.contrib import admin

from .models import FavoriteCity


@admin.register(FavoriteCity)
class FavoriteCityAdmin(admin.ModelAdmin):
    list_display = ("user", "city_slug", "created_at")
    list_filter = ("created_at",)
    search_fields = ("city_slug", "user__username")
    raw_id_fields = ("user",)
