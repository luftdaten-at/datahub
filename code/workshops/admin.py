from django.contrib import admin
from .models import Participant, Workshop

class WorkshopAdmin(admin.ModelAdmin):
    list_display = ('title', 'name', 'start_date')
    readonly_fields = ('name',)

admin.site.register(Workshop, WorkshopAdmin)

class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('name', 'workshop', 'device')

admin.site.register(Participant, ParticipantAdmin)