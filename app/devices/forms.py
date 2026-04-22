from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Device


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = '__all__'

class DeviceNotesForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ['notes']  # Only include the 'notes' field
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter notes here...',
            }),
        }


class DeviceApikeyForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ['api_key']
        widgets = {
            'api_key': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter API key...',
                'autocomplete': 'off',
            }),
        }

    def clean_api_key(self):
        key = self.cleaned_data.get('api_key')
        if key is None or not str(key).strip():
            raise ValidationError(_('API key is required.'))
        key = str(key).strip()
        min_len = settings.STATION_APIKEY_MIN_LENGTH
        if len(key) < min_len:
            raise ValidationError(
                _('The API key must be at least %(min)d characters long.'),
                params={'min': min_len},
            )
        return key