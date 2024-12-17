from django.views.generic import View, FormView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse

from .models import Campaign, Room, Organization
from .forms import CampaignForm, CampaignUserForm, OrganizationForm


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
        This method is overridden to only include campaigns that are public or owned by the current user.
        """
        user = self.request.user
        return Campaign.objects.filter(public=True) | Campaign.objects.filter(owner=user)
    
    def get_object(self, queryset=None):
        """
        This method is overridden to provide additional checks for the Campaign's visibility.
        If the requested Campaign is not public, it raises a 404.
        """
        queryset = self.get_queryset() if queryset is None else queryset
        obj = super().get_object(queryset=queryset)
        
        if not obj.public and obj.owner != self.request.user:
            raise Http404("No campaign found matching the query")

        return obj


class CampaignsCreateView(CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'campaigns/form.html'
    success_url = reverse_lazy('campaigns-my')  # Redirect after a successful creation

    def get_initial(self):
        initial = super().get_initial()
        initial['user'] = self.request.user  # Pass the logged-in user to the form's initial data
        return initial

    def form_valid(self, form):
        form.instance.owner = self.request.user  # Set the owner to the current user
        return super().form_valid(form)
    

class CampaignsUpdateView(UpdateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'campaigns/form.html'  # Reuse the form template

    def get_initial(self):
        initial = super().get_initial()
        initial['user'] = self.request.user  # Pass the logged-in user to the form's initial data
        return initial

    def get_success_url(self):
        return reverse_lazy('campaigns-my')  # Redirect to the campaign list after update

    def form_valid(self, form):
        return super().form_valid(form)


class CampaignAddUserView(UpdateView):
    model = Campaign
    form_class = CampaignUserForm
    template_name = 'campaigns/add_user.html'

    def get_success_url(self):
        return reverse_lazy('campaigns-detail', kwargs={'pk': self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        initial['campaign'] = self.object # Pass the logged-in user to the form's initial data
        return initial


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


class RoomDetailView(DetailView):
    model = Room
    template_name = 'campaigns/room/detail.html'
    context_object_name = 'room'


class RoomDeleteView(DeleteView):
    model = Room
    template_name = 'campaigns/confirm_room_delete.html'
    def get_success_url(self):
        return reverse_lazy('campaigns-detail', kwargs={'pk': self.object.campaign.pk})

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(campaign__owner=self.request.user)
        return queryset


class RoomCreateView(CreateView):
    model = Room
    fields = ['name']  # Exclude 'campaign' from the form fields
    template_name = 'campaigns/room_form.html'  # Specify your template

    def dispatch(self, request, *args, **kwargs):
        self.campaign_pk = kwargs.get('campaign_pk')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        campaign = Campaign.objects.get(pk=self.campaign_pk)
        form.instance.campaign = campaign
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('campaigns-detail', kwargs={'pk': self.campaign_pk})


class OrganizationsView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = 'campaigns/my_organizations.html'
    context_object_name = 'owned_organizations'

    def get_queryset(self):
        # Return organizations where the user is the owner
        return Organization.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add organizations where the user is a member
        context['member_organizations'] = Organization.objects.filter(users=self.request.user)
        return context


class OrganizationCreateView(LoginRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'campaigns/create_organization.html'
    success_url = reverse_lazy('organizations-my')  # Redirect to a list view or another page

    def form_valid(self, form):
        organization = form.save(commit=False)
        organization.owner = self.request.user  # Set the current user as the owner
        organization.save()
        organization.users.add(self.request.user)
        form.save_m2m()  # Save the many-to-many relationships
        return super().form_valid(form)
