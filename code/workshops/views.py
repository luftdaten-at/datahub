from django.utils import timezone
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

from .models import Workshop

class WorkshopListView(ListView):
    model = Workshop
    context_object_name = 'workshops'
    template_name = 'workshops/workshop_list.html'

    def get_queryset(self):
        # Return the Workshop queryset ordered by 'title' in ascending order
        return Workshop.objects.all().filter(end_date__gt=timezone.now())


class WorkshopDetailView(DetailView):
    model = Workshop
    context_object_name = 'workshop'
    template_name = 'workshops/workshop_detail.html'