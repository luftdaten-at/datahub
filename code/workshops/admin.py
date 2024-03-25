from django.contrib import admin
from .models import Workshop

class WorkshopAdmin(admin.ModelAdmin):
    list_display = ('title', 'name', 'start_date')
    readonly_fields = ('name',)  # Make 'id' read-only but visible

admin.site.register(Workshop, WorkshopAdmin)