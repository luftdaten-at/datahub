from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Workshop

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class WorkshopForm(forms.ModelForm):
    class Meta:
        model = Workshop
        fields = ['title', 'description', 'start_date', 'end_date', 'public', 'heat_hotspots_enabled']
        labels = {
            'title': _('Title'),
            'description': _('Description'),
            'start_date': _('Start Date'),
            'end_date': _('End Date'),
            'public': _('Public'),
            'heat_hotspots_enabled': _('Heat Hotspots Enabled'),
        }
        help_texts = {
            'title': _('Enter the title of the workshop.'),
            'description': _('Write some lines about the workshop. Where does it take place? Is it associated with an event or a project? Who can participate?'),
            'public': _('Should the workshop be publicly available on the Datahub? If not, only logged-in users with set permissions can see the results.'),
            'heat_hotspots_enabled': _('Enable heat hotspots and coolspots functionality on the workshop map. This allows users to draw and visualize hot and cool areas.'),
        }
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
        }
    
    def __init__(self, *args, **kwargs):
        super(WorkshopForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.add_input(Submit('submit', 'Save'))
        # Ensure the input formats match the widget format
        self.fields['start_date'].input_formats = ('%Y-%m-%dT%H:%M',)
        self.fields['end_date'].input_formats = ('%Y-%m-%dT%H:%M',)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


class FileFieldForm(forms.Form):
    file_field = MultipleFileField()


class ImportDataForm(forms.Form):
    json_file = forms.FileField(
        label=_('JSON File'),
        help_text=_('Upload a JSON file in the Luftdaten.at JSON Trip format.')
    )
