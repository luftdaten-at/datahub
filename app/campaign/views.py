import statistics

from datetime import datetime, timedelta
from collections import defaultdict
from django.http import Http404
from django.views.generic import View, FormView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail

from main import settings
from .models import Campaign, Room, Organization, OrganizationInvitation
from .forms import CampaignForm, CampaignUserForm, OrganizationForm, RoomDeviceForm
from accounts.models import CustomUser
from main.enums import Dimension


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
        
        if not self.request.user.is_superuser and not obj.public and obj.owner != self.request.user:
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
        initial['campaign'] = self.object
        return initial


class RoomAddDeviceView(UpdateView):
    model = Room 
    form_class = RoomDeviceForm
    template_name = 'campaigns/room/add_device.html'

    def get_success_url(self):
        return reverse_lazy('room-detail', kwargs={'pk': self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        initial['room'] = self.object
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

    def get_context_data(self, **kwargs):
        # Get the default context data
        context = super().get_context_data(**kwargs)

        # Add custom variables to the context
        # context['custom_variable'] = 'Your custom value here'
        # context['additional_data'] = Device.objects.filter(room=self.object)  # Example of another custom variable

        room = self.object
        measurements = room.measurements.all()

        measurements = [
            m for m in measurements
            if m.time_measured == room.measurements.filter(device=m.device).order_by('-time_measured').first().time_measured
        ]

        def get_current_mean(dimension):
            """
            Gibt den Durchschnittswert über alle neuesten Measurements für eine gegebene Dimension zurück.
            Wenn keine Werte vorliegen, wird None zurückgegeben.
            """
            # Für jedes Measurement sammeln wir alle Values der gesuchten Dimension
            # und bilden einen Mittelwert für dieses Measurement.
            # Anschließend bilden wir aus diesen Mittelwerten den Gesamtmittelwert.
            measurement_means = []
            for m in measurements:
                dim_values = [val.value for val in m.values.all() if val.dimension == dimension]
                if dim_values:  # Nur wenn tatsächlich Werte vorhanden sind
                    measurement_means.append(statistics.mean(dim_values))

            # Falls keine Werte gefunden, None zurückgeben
            if measurement_means:
                return statistics.mean(measurement_means)
            return None

        # Temperatur
        current_temperature = get_current_mean(Dimension.TEMPERATURE)
        temperature_color = Dimension.get_color(Dimension.TEMPERATURE, current_temperature) if current_temperature else None

        # PM2.5
        current_pm2_5 = get_current_mean(Dimension.PM2_5)
        pm2_5_color = Dimension.get_color(Dimension.PM2_5, current_pm2_5) if current_pm2_5 else None

        # CO2
        current_co2 = get_current_mean(Dimension.CO2)
        co2_color = Dimension.get_color(Dimension.CO2, current_co2) if current_co2 else None

        # VOC Index
        current_tvoc = get_current_mean(Dimension.TVOC)
        tvoc_color = Dimension.get_color(Dimension.TVOC, current_tvoc) if current_tvoc else None

        # data 24h
        now = datetime.utcnow()
        points = defaultdict(list)

        measurements = room.measurements.filter(time_measured__gt = datetime.utcnow() - timedelta(days=1)).all()
        for m in measurements:
            points[m.time_measured].append(m)
        
        print([t.strftime("%H:%M") for t in points.keys()])
        data_24h = [[t.strftime("%H:%M") for t in points.keys()], [], [], [], []]

        for time_measured, measurements in points.items():

            data = [
                [val.value
                    for m in measurements
                        for val in m.values.all()
                            if val.dimension == target_dim
                ] for target_dim in (Dimension.TEMPERATURE, Dimension.PM2_5, Dimension.CO2, Dimension.TVOC)
            ]
            for i, x in enumerate(data):
                data_24h[i + 1].append(statistics.mean(x) if x else 0)
            #data_24h.append(tuple(statistics.mean(x) if x else None for x in data))

        # group by time measured mean over dim

        # Werte ins Context-Objekt packen
        context['current_temperature'] = f'{current_temperature:.2f}' if current_temperature else None
        context['temperature_color'] = temperature_color
        context['current_pm2_5'] = f'{current_pm2_5:.2f}' if current_pm2_5 else None
        context['pm2_5_color'] = pm2_5_color
        context['current_co2'] = f'{current_co2:.2f}' if current_co2 else None
        context['co2_color'] = co2_color  
        context['current_tvoc'] = f'{current_tvoc:.2f}' if current_tvoc else None
        context['tvoc_color'] = tvoc_color
        context['data_24h'] = data_24h

        return context


class ParticipantDetailView(DetailView):
    model = CustomUser
    template_name = 'campaigns/participant/detail.html'
    context_object_name = 'participant'
    pk_url_kwarg = 'user'

    def test_func(self):
        # Define permission logic. For example, only superusers or campaign organizers can view.
        user = self.request.user
        return user.is_authenticated and user.is_superuser  # Adjust as needed

    def get_queryset(self):
        """
        Optionally, restrict the queryset to users associated with the campaign.
        This ensures that users not part of the campaign cannot access details.
        """
        campaign_pk = self.kwargs.get('pk')  # Campaign's pk from URL
        return CustomUser.objects.filter(campaigns__pk=campaign_pk)  # Adjust the relationship as per your models

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        participant = self.object
        measurements = participant.measurements.all()
        

        measurements = [
            m for m in measurements
            if m.time_measured == participant.measurements.filter(device=m.device).order_by('-time_measured').first().time_measured
        ]

        def get_current_mean(dimension):
            """
            Gibt den Durchschnittswert über alle neuesten Measurements für eine gegebene Dimension zurück.
            Wenn keine Werte vorliegen, wird None zurückgegeben.
            """
            # Für jedes Measurement sammeln wir alle Values der gesuchten Dimension
            # und bilden einen Mittelwert für dieses Measurement.
            # Anschließend bilden wir aus diesen Mittelwerten den Gesamtmittelwert.
            measurement_means = []
            for m in measurements:
                dim_values = [val.value for val in m.values.all() if val.dimension == dimension]
                if dim_values:  # Nur wenn tatsächlich Werte vorhanden sind
                    measurement_means.append(statistics.mean(dim_values))

            # Falls keine Werte gefunden, None zurückgeben
            if measurement_means:
                return statistics.mean(measurement_means)
            return None

        # Temperatur
        current_temperature = get_current_mean(Dimension.TEMPERATURE)
        temperature_color = Dimension.get_color(Dimension.TEMPERATURE, current_temperature) if current_temperature else None

        # VOC Index
        current_uvi = get_current_mean(Dimension.UVI)
        uvi_color = Dimension.get_color(Dimension.UVI, current_uvi) if current_uvi else None

        # data 24h
        now = datetime.utcnow()
        points = defaultdict(list)

        measurements = participant.measurements.filter(time_measured__gt = datetime.utcnow() - timedelta(days=1)).all()
        for m in measurements:
            points[m.time_measured].append(m)
        
        print([t.strftime("%H:%M") for t in points.keys()])
        data_24h = [[t.strftime("%H:%M") for t in points.keys()], [], [], [], []]

        for time_measured, measurements in points.items():

            data = [
                [val.value
                    for m in measurements
                        for val in m.values.all()
                            if val.dimension == target_dim
                ] for target_dim in (Dimension.TEMPERATURE, Dimension.PM2_5, Dimension.CO2, Dimension.TVOC)
            ]
            for i, x in enumerate(data):
                data_24h[i + 1].append(statistics.mean(x) if x else 0)
            #data_24h.append(tuple(statistics.mean(x) if x else None for x in data))

        # group by time measured mean over dim

        # Werte ins Context-Objekt packen
        context['current_temperature'] = f'{current_temperature:.2f}' if current_temperature else None
        context['temperature_color'] = temperature_color
        context['current_uvi'] = f'{current_uvi:.2f}' if current_uvi else None
        context['uvi_color'] = uvi_color
        context['data_24h'] = data_24h

        return context


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


class OrganizationDetailView(DetailView):
    model = Organization
    template_name = 'campaigns/organization_detail.html'
    context_object_name = 'organization'

    def get_success_url(self):
        # and 'self.object.pk' with the primary key of the newly created object
        return reverse_lazy('organizations-my', kwargs={'pk': self.object.pk})


@login_required
def remove_user_from_organization(request, org_id, user_id):
    organization = get_object_or_404(Organization, id=org_id)
    user = get_object_or_404(CustomUser, id=user_id)

    # Ensure the user performing the action has permission
    if request.user != organization.owner:
        messages.error(request, "You do not have permission to remove users from this organization.")
        return redirect('organization-detail', pk=org_id)

    organization.users.remove(user)
    messages.success(request, f"User {user.username} has been removed.")
    return redirect('organization-detail', pk=org_id)


@login_required
def invite_user_to_organization(request, org_id):
    if request.method != 'POST':
        return redirect(f"organization-detail", pk=org_id)

    organization = get_object_or_404(Organization, id=org_id)
    email = request.POST.get('email')
    
    if request.user != organization.owner:
        messages.error(request, "You do not have permission to invite users to this organization.")
        return redirect(f"organization-detail", pk=org_id)

    user = CustomUser.objects.filter(email = email).first()

    if user:
        organization.users.add(user)
    else:
        # check if invitation already exists
        invitation = OrganizationInvitation.objects.filter(email=email, organization__pk = organization.pk).first()
        if invitation == None:
            # create invitation
            invitation = OrganizationInvitation(
                expiring_date = None,
                email = email,
                organization = organization,
            )
        invitation.save()
        # send invitation email
        # TODO add link to register
        send_mail(
            subject=f"You've been invited to join {organization.name}",
            message=f"Visit this link to register and join {organization.name}: <registration_link>",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
        )
        messages.success(request, f"An invitation has been sent to {email}.")

    return redirect(f"organization-detail", pk=org_id)
