from django.utils import timezone
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

from .models import Workshop

class WorkshopListView(ListView):
    model = Workshop
    context_object_name = 'workshops'
    template_name = 'workshops/workshop_list.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        
        # Filter workshops that are public and whose end_date is in the future
        context['upcoming_workshops'] = Workshop.objects.filter(end_date__gt=timezone.now(), public=True).order_by('end_date')
        
        # Filter workshops that are public and whose end_date is in the past
        context['past_workshops'] = Workshop.objects.filter(end_date__lte=timezone.now(), public=True).order_by('end_date')
        
        return context


class WorkshopDetailView(DetailView):
    model = Workshop
    context_object_name = 'workshop'
    template_name = 'workshops/workshop_detail.html'

    def get_queryset(self):
        """
        This method is overridden to only include workshops that are public.
        """
        # Only fetch workshops that are public.
        return Workshop.objects.filter(public=True)
    
    def get_object(self, queryset=None):
        """
        This method is overridden to provide additional checks for the workshop's visibility.
        If the requested workshop is not public, it raises a 404.
        """
        # Use the filtered queryset from get_queryset to ensure we're only considering public workshops.
        queryset = self.get_queryset() if queryset is None else queryset
        obj = super().get_object(queryset=queryset)  # This gets the object using the queryset we provided.
        
        # If the workshop is not public and the user is not the owner, raise a 404 error.
        if not obj.public and obj.owner != self.request.user:
            raise Http404("No workshop found matching the query")

        # Optionally, you could check for additional conditions here, like user permissions or roles.

        return obj