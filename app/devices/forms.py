from django import forms
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