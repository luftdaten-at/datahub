from django.contrib import admin
from django.contrib.sites.models import Site

from .models import FAQEntry


@admin.register(FAQEntry)
class FAQEntryAdmin(admin.ModelAdmin):
    list_display = (
        "question",
        "sort_order",
        "is_published",
        "updated_at",
    )
    list_editable = ("sort_order", "is_published")
    list_filter = ("is_published",)
    search_fields = ("question", "answer")
    ordering = ("sort_order", "pk")

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# Unregister the Site model from admin
admin.site.unregister(Site)