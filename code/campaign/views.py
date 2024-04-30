from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from .models import Campaign
from .forms import CampaignForm


class CampaignsHomeView(ListView):
    model = Campaign
    template_name = 'campaigns/home.html'
    context_object_name = 'campaigns'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        
        # Filter campaigns by their end_date
        context['campaigns'] = Campaign.objects.all().order_by('end_date')
        
        return context


class CampaignsMyView(LoginRequiredMixin, ListView):
    model = Campaign
    template_name = 'campaigns/my.html'
    context_object_name = 'campaigns'

    def test_func(self):
        return self.request.user.is_authenticated 

    def get_queryset(self):
        # Return the Device queryset ordered by 'name' in ascending order
        return Campaign.objects.all().order_by('name')

class CampaignsDetailView(DetailView):
    model = Campaign
    context_object_name = 'campaign'
    template_name = 'campaigns/detail.html'

    def get_queryset(self):
        """
        This method is overridden to only include campaigns that are public.
        """
        # Only fetch Campaigns that are public.
        return Campaign.objects.filter(public=True)
    
    def get_object(self, queryset=None):
        """
        This method is overridden to provide additional checks for the Campaign's visibility.
        If the requested Campaign is not public, it raises a 404.
        """
        # Use the filtered queryset from get_queryset to ensure we're only considering public Campaigns.
        queryset = self.get_queryset() if queryset is None else queryset
        obj = super().get_object(queryset=queryset)  # This gets the object using the queryset we provided.
        
        # If the Campaign is not public and the user is not the owner, raise a 404 error.
        if not obj.public and obj.owner != self.request.user:
            raise Http404("No campaign found matching the query")

        return obj


class CampaignsCreateView(CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'campaigns/form.html'
    success_url = reverse_lazy('campaigns-my')  # Redirect after a successful creation

    def form_valid(self, form):
        form.instance.owner = self.request.user  # Set the owner to the current user
        return super().form_valid(form)
    

class CampaignsUpdateView(UpdateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'campaigns/form.html'  # Reuse the form template

    def get_success_url(self):
        return reverse_lazy('campaigns-my')  # Redirect to the campaign list after update

    def form_valid(self, form):
        return super().form_valid(form)
    

class CampaignsDeleteView(DeleteView):
    model = Campaign
    template_name = 'campaigns/confirm_delete.html'  # Confirmation page template
    success_url = reverse_lazy('campaigns-my')  # Redirect here after deletion

    def get_queryset(self):
        queryset = super().get_queryset()
        # Optional: restrict deletion to the owner or admin
        if not self.request.user.is_superuser:
            queryset = queryset.filter(owner=self.request.user)
        return queryset