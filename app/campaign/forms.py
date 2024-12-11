from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Campaign, Organization
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
        
        # Get the user from the passed arguments (initial data)
        self.user = kwargs.get('initial', {}).get('user', None)
        
        # Initialize form helper
        self.helper = FormHelper(self)
        self.helper.add_input(Submit('submit', 'Save'))
        
        # Ensure the input formats match the widget format
        self.fields['start_date'].input_formats = ('%Y-%m-%dT%H:%M',)
        self.fields['end_date'].input_formats = ('%Y-%m-%dT%H:%M',)

    def save(self, commit=True):
        # Get the instance but don't save to the database yet
        campaign = super().save(commit=False)

        # Set the `public` field to False
        campaign.public = False
        campaign.owner = self.user
        campaign.users.add(self.user)
        campaign.organization = self.user.organizations.first()

        # Save to the database if commit is True
        if commit:
            campaign.save()
        
        return campaign 


class CampaignUserForm(forms.ModelForm):
    search_query = forms.CharField(
        required=False,
        label="Search Users",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search for users...'})
    )
    users = forms.ModelMultipleChoiceField(
        queryset=None,  # Initially no queryset
        widget=forms.CheckboxSelectMultiple(),
        label="Select Users",
    )

    class Meta:
        model = Campaign
        fields = []  # We are not modifying Campaign fields here, just adding users

    def __init__(self, *args, **kwargs):
        """
        Accept the campaign object via kwargs and use it to set the correct queryset for users.
        """
        self.campaign = kwargs.pop('campaign', None)  # The campaign is passed to the form
        super().__init__(*args, **kwargs)

        if self.campaign:
            # Exclude users who are already in the campaign
            self.fields['users'].queryset = self.campaign.organization.users.all()

    def save(self, commit=True):
        """
        Save the selected users to the campaign.
        """
        campaign = super().save(commit=False)  # We don't save the campaign yet
        users = self.cleaned_data['users']  # Get the selected users
        campaign.users.add(*users)  # Add users to the campaign's many-to-many relationship
        if commit:
            campaign.save()  # Save the campaign (if commit=True)
        return campaign
