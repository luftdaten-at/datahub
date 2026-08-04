from django.contrib import admin, messages
from django.contrib.gis import admin as gis_admin

from .imports import accept
from .models import (
    DatasetImport,
    Municipality,
    MunicipalityHeatProfile,
    MunicipalityLandProfile,
    PeerGroup,
)

class ReadOnlyProfileAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Municipality)
class MunicipalityAdmin(gis_admin.GISModelAdmin):
    list_display = (
        "name",
        "slug",
        "gkz",
        "match_method",
        "match_confidence",
        "has_boundary",
    )
    list_filter = ("match_method", "country_code")
    search_fields = ("name", "slug", "gkz")
    actions = ["confirm_match"]

    @admin.display(boolean=True, description="Boundary")
    def has_boundary(self, obj):
        return obj.boundary is not None

    @admin.action(description="Zuordnung als manuell bestätigt markieren")
    def confirm_match(self, request, queryset):
        updated = queryset.update(match_method=Municipality.MATCH_MANUAL)
        self.message_user(
            request,
            f"{updated} Gemeinde(n) als manuell bestätigt markiert.",
            messages.SUCCESS,
        )


@admin.register(PeerGroup)
class PeerGroupAdmin(admin.ModelAdmin):
    list_display = ("key", "label_de", "label_en")
    search_fields = ("key", "label_de", "label_en")


@admin.register(MunicipalityLandProfile)
class MunicipalityLandProfileAdmin(ReadOnlyProfileAdmin):
    list_display = (
        "municipality",
        "reference_year",
        "imperviousness_pct",
        "tree_cover_pct",
        "data_source",
    )
    search_fields = ("municipality__slug", "municipality__name")


@admin.register(MunicipalityHeatProfile)
class MunicipalityHeatProfileAdmin(ReadOnlyProfileAdmin):
    list_display = (
        "municipality",
        "reference_date",
        "lst_mean",
        "clear_fraction",
        "sensor",
    )
    search_fields = ("municipality__slug", "municipality__name")


@admin.register(DatasetImport)
class DatasetImportAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "module",
        "reference_date",
        "status",
        "profiles_in_file",
        "profiles_written",
        "error_count",
    )
    list_filter = ("module", "status")
    readonly_fields = (
        "source_sha256",
        "source_path",
        "manifest",
        "validation_report",
        "profiles_in_file",
        "profiles_written",
        "profiles_flagged",
        "accepted_at",
        "created_at",
    )
    actions = ["accept_selected", "reject_selected"]

    @admin.display(description="Fehler")
    def error_count(self, obj):
        return len(obj.validation_report.get("errors", []))

    @admin.action(description="Ausgewählte Übernahmen bestätigen")
    def accept_selected(self, request, queryset):
        for imp in queryset.filter(status=DatasetImport.STATUS_PENDING):
            result = accept(imp)
            level = messages.SUCCESS if result.ok else messages.ERROR
            self.message_user(request, str(imp), level=level)

    @admin.action(description="Ausgewählte Übernahmen ablehnen")
    def reject_selected(self, request, queryset):
        count = queryset.filter(status=DatasetImport.STATUS_PENDING).update(
            status=DatasetImport.STATUS_REJECTED
        )
        self.message_user(request, f"{count} Übernahme(n) abgelehnt.", messages.SUCCESS)
