from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Campaign, Organization

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


from django.conf import settings

class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['name', 'description', 'start_date', 'end_date', 'public', 'organization', 'users']
        labels = {
            'name': _('Name'),
            'description': _('Description'),
            'start_date': _('Start Date'),
            'end_date': _('End Date'),
            'public': _('Public'),
            'organization': _('Organization'),
            'users': _('Users'),
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
        
        # Get the user from the passed arguments (initial data)
        user = kwargs.get('initial', {}).get('user', None)
        
        # If a user is provided, filter the organizations based on the user's membership
        print(user.organizations.all())
        if user:
            self.fields['organization'].queryset = user.organizations.all()  # Only show organizations the user belongs to
        else:
            self.fields['organization'].queryset = Organization.objects.none()  # If no user, don't display any organizations
            
        # Initialize form helper
        self.helper = FormHelper(self)
        self.helper.add_input(Submit('submit', 'Save'))
        
        # Ensure the input formats match the widget format
        self.fields['start_date'].input_formats = ('%Y-%m-%dT%H:%M',)
        self.fields['end_date'].input_formats = ('%Y-%m-%dT%H:%M',)
