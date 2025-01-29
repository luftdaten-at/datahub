import statistics
import numpy as np

from datetime import datetime, timedelta, timezone
from collections import defaultdict
from django.core.exceptions import PermissionDenied
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Max, Q


from .models import Campaign, Room
from devices.models import Values
from .forms import CampaignForm, CampaignUserForm, RoomDeviceForm, UserDeviceForm
from accounts.models import CustomUser
from main.enums import Dimension, SensorModel
from functools import reduce


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['member_campaigns'] = Campaign.objects.filter(users=user)
        context['owner_campaigns'] = Campaign.objects.filter(owner=user)
        context['campaigns'] = Campaign.objects.all() if user.is_superuser else context['member_campaigns']

        return context


class CampaignsDetailView(LoginRequiredMixin, DetailView):
    model = Campaign
    context_object_name = 'campaign'
    template_name = 'campaigns/detail.html'

    def get_object(self, queryset = None): 
        campaign = super().get_object(queryset)
        user = self.request.user

        if user.is_superuser:
            return campaign
        if not campaign.users.filter(id=user.id).exists():
            raise PermissionDenied('You are not allowed to view this Campaign')
        return campaign

class CampaignsCreateView(LoginRequiredMixin, CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'campaigns/form.html'
    success_url = reverse_lazy('campaigns-my')  # Redirect after a successful creation

    def form_valid(self, form):
        # Get the instance but don't save to the database yet
        campaign = form.save(commit=False)
        # Set the `public` field to False
        campaign.public = False
        campaign.owner = self.request.user
        campaign.organization = self.request.user.organizations.first()
        campaign.save()
        campaign.users.add(self.request.user)
        campaign.save()

        return super().form_valid(form)


class CampaignsUpdateView(LoginRequiredMixin, UpdateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'campaigns/form.html'
    success_url = reverse_lazy('campaigns-my')  # Redirect after a successful creation

    def get_object(self, queryset = None):
        campaign = super().get_object(queryset)
        user = self.request.user
        
        if user.is_superuser:
            return campaign
        if user != campaign.owner:
            raise PermissionDenied('You are not allowed to update this Campaign')
        return campaign


class CampaignAddUserView(LoginRequiredMixin, UpdateView):
    model = Campaign
    form_class = CampaignUserForm
    template_name = 'campaigns/add_user.html'

    def get_success_url(self):
        return reverse_lazy('campaigns-detail', kwargs={'pk': self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        initial['campaign'] = self.object
        return initial

    def get_object(self, queryset = None):
        campaign = super().get_object(queryset)
        user = self.request.user
        
        if user.is_superuser:
            return campaign
        if user != campaign.owner:
            raise PermissionDenied('You are not allowed to update this Campaign')
        return campaign


class RoomAddDeviceView(LoginRequiredMixin, UpdateView):
    model = Room 
    form_class = RoomDeviceForm
    template_name = 'campaigns/room/add_device.html'

    def get_success_url(self):
        return reverse_lazy('room-detail', kwargs={'pk': self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        initial['room'] = self.object
        return initial 
    
    def get_object(self, queryset = None):
        room = super().get_object(queryset)
        user = self.request.user
        
        if user.is_superuser:
            return room
        if user != room.campaign.owner:
            raise PermissionDenied('You are not allowed to update this Campaign')
        return room


class CampaignsDeleteView(LoginRequiredMixin, DeleteView):
    model = Campaign
    template_name = 'campaigns/confirm_delete.html'  # Confirmation page template
    success_url = reverse_lazy('campaigns-my')  # Redirect here after deletion

    def get_object(self, queryset = None):
        campaign = super().get_object(queryset)
        user = self.request.user
        
        if user.is_superuser:
            return campaign
        if user != campaign.owner:
            raise PermissionDenied('You are not allowed to update this Campaign')
        return campaign


class RoomDetailView(LoginRequiredMixin, DetailView):
    model = Room
    template_name = 'campaigns/room/detail.html'
    context_object_name = 'room'

    def get_object(self, queryset = None):
        room = super().get_object(queryset)
        user = self.request.user

        if user.is_superuser:
            return room
        if not room.campaign.users.filter(id=user.id).exists():
            raise PermissionDenied('You are not allowed to update this Campaign')
        return room

    def get_context_data(self, **kwargs):
        # Get the default context data
        context = super().get_context_data(**kwargs)

        room = self.object

        max_time_measured_per_device = room.measurements.values('device').annotate(max_time_measured=Max('time_measured'))

        measurements = []
        for entry in max_time_measured_per_device:
            measurements.extend(room.measurements.filter(device = entry['device'], time_measured = entry['max_time_measured']).all())

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
        measurements_adjusted_temp_cube = [
            value.value 
            for m in measurements
                if m.sensor_model == SensorModel.VIRTUAL_SENSOR
                    for value in m.values.all()
                        if value.dimension == Dimension.ADJUSTED_TEMP_CUBE
        ]

        current_temperature = None
        # use ADJUSTED_TEMP_CUBE if found
        if measurements_adjusted_temp_cube:
            current_temperature = measurements_adjusted_temp_cube[0]
            temperature_color = Dimension.get_color(Dimension.ADJUSTED_TEMP_CUBE, current_temperature) if current_temperature else None
        else:
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

        # dimensions to be displayed
        target_dimensions = (Dimension.TEMPERATURE, Dimension.PM2_5, Dimension.CO2, Dimension.TVOC)
        time_range = timedelta(days=1)
        start_time = datetime.now(timezone.utc) - time_range

        all_values = Values.objects.filter(
            measurement__time_measured__gt = start_time,
            measurement__room = room,
        ).filter(
            # Get only the values with target dimension
            reduce(lambda a, b: a | b, [Q(dimension = dim) for dim in target_dimensions], Q())
        ).values(
            'dimension',
            'value',
            'measurement__time_measured'
        )

        sum_24h = np.zeros((len(target_dimensions), int(time_range.total_seconds() // 60)))
        cnt_24h = np.zeros_like(sum_24h)
        dim_id = {dim: i for i, dim in enumerate(target_dimensions)}

        for val in all_values:
            sum_24h[dim_id[val['dimension']]][int((val['measurement__time_measured'] - start_time).total_seconds() // 60)] += val['value']
            cnt_24h[dim_id[val['dimension']]][int((val['measurement__time_measured'] - start_time).total_seconds() // 60)] += 1
        
        data_24h = sum_24h / cnt_24h
        labels = [(start_time + timedelta(minutes=i)).strftime("%H:%M") for i in range(int(time_range.total_seconds() // 60))]

        # Werte ins Context-Objekt packen
        context['current_temperature'] = f'{current_temperature:.2f}' if current_temperature else None
        context['temperature_color'] = temperature_color
        context['current_pm2_5'] = f'{current_pm2_5:.2f}' if current_pm2_5 else None
        context['pm2_5_color'] = pm2_5_color
        context['current_co2'] = f'{current_co2:.2f}' if current_co2 else None
        context['co2_color'] = co2_color  
        context['current_tvoc'] = f'{current_tvoc:.2f}' if current_tvoc else None
        context['tvoc_color'] = tvoc_color
        context['data_24h'] = np.nan_to_num(data_24h, nan=0).tolist()
        context['labels'] = labels


        return context


class ParticipantDetailView(LoginRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'campaigns/participants/detail.html'
    context_object_name = 'participant'
    pk_url_kwarg = 'user'


    def dispatch(self, request, *args, **kwargs):
        self.campaign = get_object_or_404(Campaign, pk=kwargs['pk'])

        if self.request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        # only users in campaign
        if not self.campaign.users.filter(id = self.request.user.id).exists():
            raise PermissionDenied("You are not allowed to create a Room")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object

        max_time_measured_per_device = user.measurements.values('device').annotate(max_time_measured=Max('time_measured'))

        measurements = []
        for entry in max_time_measured_per_device:
            measurements.extend(user.measurements.filter(device = entry['device'], time_measured = entry['max_time_measured']).all())

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


        # dimensions to be displayed
        target_dimensions = (Dimension.TEMPERATURE, Dimension.UVI)
        time_range = timedelta(days=1)
        start_time = datetime.now(timezone.utc) - time_range

        all_values = Values.objects.filter(
            measurement__time_measured__gt = start_time,
            measurement__user = user,
            measurement__device__current_campaign = self.campaign
        ).filter(
            # Get only the values with target dimension
            reduce(lambda a, b: a | b, [Q(dimension = dim) for dim in target_dimensions], Q())
        ).values(
            'dimension',
            'value',
            'measurement__time_measured'
        )

        sum_24h = np.zeros((len(target_dimensions), int(time_range.total_seconds() // 60)))
        cnt_24h = np.zeros_like(sum_24h)
        dim_id = {dim: i for i, dim in enumerate(target_dimensions)}

        for val in all_values:
            sum_24h[dim_id[val['dimension']]][int((val['measurement__time_measured'] - start_time).total_seconds() // 60)] += val['value']
            cnt_24h[dim_id[val['dimension']]][int((val['measurement__time_measured'] - start_time).total_seconds() // 60)] += 1
        
        data_24h = sum_24h / cnt_24h
        labels = [(start_time + timedelta(minutes=i)).strftime("%H:%M") for i in range(int(time_range.total_seconds() // 60))]

        # Werte ins Context-Objekt packen
        context['current_temperature'] = f'{current_temperature:.2f}' if current_temperature else None
        context['temperature_color'] = temperature_color
        context['current_tvoc'] = f'{current_uvi:.2f}' if current_uvi else None
        context['tvoc_color'] = uvi_color 
        context['data_24h'] = np.nan_to_num(data_24h, nan=0).tolist()
        context['labels'] = labels

        context['campaign'] = self.campaign
        context['device_list'] = user.current_devices.filter(current_campaign=self.campaign)

        return context


class RoomDeleteView(LoginRequiredMixin, DeleteView):
    model = Room
    template_name = 'campaigns/confirm_room_delete.html'

    def get_success_url(self):
        return reverse_lazy('campaigns-detail', kwargs={'pk': self.object.campaign.pk})

    def get_object(self, queryset = None):
        room = super().get_object(queryset)
        user = self.request.user
        
        if user.is_superuser:
            return room
        if user != room.campaign.owner:
            raise PermissionDenied('You are not allowed to update this Campaign')
        return room


class RoomCreateView(LoginRequiredMixin, CreateView):
    model = Room
    fields = ['name']  # Exclude 'campaign' from the form fields
    template_name = 'campaigns/room_form.html'  # Specify your template

    def dispatch(self, request, *args, **kwargs):
        self.campaign = Campaign.objects.get(pk=kwargs['campaign_pk'])

        if self.request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        if self.request.user != self.campaign.owner:
            raise PermissionDenied("You are not allowed to create a Room")

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        room = form.save(commit=False)
        campaign = self.campaign

        if self.campaign.rooms.filter(name=room.name).exists():
            form.add_error('name', "A room with this name already exists in the campaign.")
            return self.form_invalid(form)

        room.campaign = campaign
        room.save()

        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('campaigns-detail', kwargs={'pk': self.campaign.pk})


class RoomUpdateView(LoginRequiredMixin, UpdateView):
    model = Room
    fields = ['name']  # Exclude 'campaign' from the form fields
    template_name = 'campaigns/room_form.html'  # Specify your template

    def dispatch(self, request, *args, **kwargs):
        self.campaign = Campaign.objects.get(pk=kwargs['campaign_pk'])

        if self.request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        if self.request.user != self.campaign.owner:
            raise PermissionDenied("You are not allowed to create a Room")

        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse_lazy('campaigns-detail', kwargs={'pk': self.campaign.pk})
    

class ParticipantsAddDevicesView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = UserDeviceForm
    template_name = 'campaigns/participants/add_device.html'

    def get_success_url(self):
        return reverse_lazy('participants-detail', kwargs={'pk': self.campaign.pk, 'user': self.object.pk})
    
    def dispatch(self, request, *args, **kwargs):
        self.campaign = Campaign.objects.get(pk=kwargs['campaign_pk'])

        if self.request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        if self.request.user != self.campaign.owner:
            raise PermissionDenied("You are not allowed to create a Room")

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial['campaign'] = self.campaign
        initial['user'] = self.object
        return initial 
