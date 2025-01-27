from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.admin.widgets import FilteredSelectMultiple

from organizations.models import Organization

from .models import Campaign, Room
from devices.models import Device
from accounts.models import CustomUser

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


from django.conf import settings

class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['name', 'description', 'start_date', 'end_date']
        labels = {
            'name': _('Name'),
            'description': _('Description'),
            'start_date': _('Start Date'),
            'end_date': _('End Date'),
        }
        help_texts = {
            'name': _('Enter the name of the campaign.'),
            'description': _('Write some lines about the Campaign. Where does it take place? Is it associated with an event or a project? Who can participate?'),
            'public': _('Should the Campaign be publicly available on the Datahub? If not, only logged-in users with set permissions can see the results.'),
        }
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize form helper
        self.helper = FormHelper(self)
        self.helper.add_input(Submit('submit', 'Save'))
        
        # Ensure the input formats match the widget format
        self.fields['start_date'].input_formats = ('%Y-%m-%dT%H:%M',)
        self.fields['end_date'].input_formats = ('%Y-%m-%dT%H:%M',)


class CampaignUserForm(forms.ModelForm):
    users = (forms.ModelMultipleChoiceField(label='',
             queryset=CustomUser.objects.none(),
             widget=FilteredSelectMultiple(
                verbose_name='Users',
                is_stacked=False,
             ),
             required=False))

    class Meta:
        model = Campaign
        fields = ['users']
    
    class Media:
        css = {
            'all': ('/static/admin/css/widgets.css', '/static/css/adminoverrides.css', ),
        } # custom css
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get the user from the passed arguments (initial data)
        self.campaign = kwargs.get('initial', {}).get('campaign', None)

        if self.campaign:
            self.fields['users'].queryset = self.campaign.organization.users.all()
        
        # Initialize form helper
        self.helper = FormHelper(self)
        self.helper.add_input(Submit('submit', 'Save'))


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class RoomDeviceForm(forms.ModelForm):
    current_devices = (forms.ModelMultipleChoiceField(label='',
             queryset=Device.objects.none(),
             widget=FilteredSelectMultiple(
                verbose_name='Devices',
                is_stacked=False,
             ),
             required=False))

    class Meta:
        model = Room 
        fields = ['current_devices']
    
    class Media:
        css = {
            'all': ('/static/admin/css/widgets.css', '/static/css/adminoverrides.css', ),
        } # custom css
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get the user from the passed arguments (initial data)
        self.room = kwargs.get('initial', {}).get('room', None)

        if self.room:
            # query set should be a list of all devices in the same organisation as the room is
            self.fields['current_devices'].queryset = self.room.campaign.organization.current_devices.all()
            self.initial['current_devices'] = self.room.current_devices.all()
        
        # Initialize form helper
        self.helper = FormHelper(self)
        self.helper.add_input(Submit('submit', 'Save'))

    def save(self, commit=True):
        # Save the room instance
        room = super().save(commit=commit)

        # Get the selected devices
        selected_devices = self.cleaned_data['current_devices']

        # Update the ForeignKey for the devices
        if commit:
            # Unassign the devices previously linked to the room
            Device.objects.filter(current_room=room).update(current_room=None)

            # Assign the selected devices to the current room
            selected_devices.update(current_room=room)
            # Update campaign
            selected_devices.update(current_campaign=room.campaign)

            # Save the room
            room.save()

        return room


class UserDeviceForm(forms.ModelForm):
    current_devices = (forms.ModelMultipleChoiceField(label='',
             queryset=Device.objects.none(),
             widget=FilteredSelectMultiple(
                verbose_name='Devices',
                is_stacked=False,
             ),
             required=False))

    class Meta:
        model = Room 
        fields = ['current_devices']
    
    class Media:
        css = {
            'all': ('/static/admin/css/widgets.css', '/static/css/adminoverrides.css', ),
        } # custom css
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get the user from the passed arguments (initial data)
        self.user = kwargs.get('initial', {}).get('user', None)
        self.campaign = kwargs.get('initial', {}).get('campaign', None)

        # query set should be a list of all devices in the same organisation as the campaign is
        self.fields['current_devices'].queryset = self.campaign.organization.current_devices.all()
        self.initial['current_devices'] = self.user.current_devices.all()
        
        # Initialize form helper
        self.helper = FormHelper(self)
        self.helper.add_input(Submit('submit', 'Save'))

    def save(self, commit=True):
        # Save the room instance
        user = super().save(commit=commit)

        # Get the selected devices
        selected_devices = self.cleaned_data['current_devices']

        # Update the ForeignKey for the devices
        if commit:
            # Unassign the devices previously linked to the room
            Device.objects.filter(current_user=user).update(current_user=None)

            # Assign the selected devices to the current room
            selected_devices.update(current_user=user)
            # Update campaign
            selected_devices.update(current_campaign=self.campaign)

            # Save the room
            user.save()

        return user
