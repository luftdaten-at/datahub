from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.admin.widgets import FilteredSelectMultiple

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

'''
class FooForm(forms.Form):
    linked_bars = forms.ModelMultipleChoiceField(queryset=Bar.objects.all(),
                         widget=widgets.FilteredSelectMultiple(Bar._meta.verbose_name_plural, False))
'''




class CampaignUserForm(forms.Form):
    users = forms.ModelMultipleChoiceField(
        queryset=None,  # Placeholder queryset
        widget=FilteredSelectMultiple("Users", False),  # Use FilteredSelectMultiple
        required=False
    )

    def __init__(self, *args, **kwargs):
        campaign = kwargs.pop('campaign', None)  # Accept the campaign instance via kwargs
        super().__init__(*args, **kwargs)
        if campaign and campaign.organization:
            # Restrict the queryset to users in the campaign's organization
            self.fields['users'].queryset = campaign.organization.users.all()


'''
class CampaignAddUserForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['users']  # Assuming 'users' is a ManyToManyField in the Campaign model
        widgets = {
            'users': FilteredSelectMultiple(verbose_name='Users', is_stacked=True),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ensure that we only show users from the associated organization
        campaign = kwargs.get('instance')
        if campaign and campaign.organization:
            print(campaign.organization.users.all())
            self.fields['users'].queryset = campaign.organization.users.all()
'''