from django.utils import timezone
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from .models import Workshop
from .forms import WorkshopForm

class WorkshopListView(ListView):
    model = Workshop
    context_object_name = 'workshops'
    template_name = 'workshops/workshops_list.html'

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

        return obj


class WorkshopMyView(LoginRequiredMixin, ListView):
    model = Workshop
    template_name = 'workshops/workshops_my.html'
    context_object_name = 'workshops'
    
    def get_queryset(self):
        if self.request.user.is_superuser:  # Check if the user is an admin
            return Workshop.objects.all()  # Admin sees all workshops
        else:
            return Workshop.objects.filter(owner=self.request.user)  # Filter by owner


class WorkshopCreateView(CreateView):
    model = Workshop
    form_class = WorkshopForm
    template_name = 'workshops/workshop_form.html'
    success_url = reverse_lazy('workshops-my')  # Redirect after a successful creation

    def form_valid(self, form):
        form.instance.owner = self.request.user  # Set the owner to the current user
        return super().form_valid(form)
    

class WorkshopUpdateView(UpdateView):
    model = Workshop
    form_class = WorkshopForm
    template_name = 'workshops/workshop_form.html'  # Reuse the form template

    def get_success_url(self):
        return reverse_lazy('workshops-my')  # Redirect to the workshop list after update

    def form_valid(self, form):
        # Optional: Add any additional logic here before saving the form
        return super().form_valid(form)
    

class WorkshopDeleteView(DeleteView):
    model = Workshop
    template_name = 'workshops/workshop_confirm_delete.html'  # Confirmation page template
    success_url = reverse_lazy('workshops-my')  # Redirect here after deletion

    def get_queryset(self):
        queryset = super().get_queryset()
        # Optional: restrict deletion to the owner or admin
        if not self.request.user.is_superuser:
            queryset = queryset.filter(owner=self.request.user)
        return queryset