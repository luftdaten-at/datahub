from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

from .models import Workshop


class WorkshopListView(ListView):
    model = Workshop
    context_object_name = 'workshops'
    template_name = 'workshops/workshop_list.html'


class WorkshopDetailView(DetailView):
    model = Workshop
    context_object_name = 'workshop'
    template_name = 'workshops/workshop_detail.html'