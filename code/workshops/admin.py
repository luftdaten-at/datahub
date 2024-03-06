from django.contrib import admin
from .models import Workshop

class WorkshopAdmin(admin.ModelAdmin):
    list_display = ('title', 'id', 'start_date')  # Customize as needed
    readonly_fields = ('id',)  # Make 'unique_id' read-only but visible

admin.site.register(Workshop, WorkshopAdmin)