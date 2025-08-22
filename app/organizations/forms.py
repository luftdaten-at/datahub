from django import forms
from django.utils.translation import gettext_lazy as _
from organizations.models import Organization


class OrganizationForm(forms.ModelForm):
    new_owner = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label=_("Keep current ownership"),
        help_text=_("Select a new owner from the organization members. Leave empty to keep current ownership.")
    )

    class Meta:
        model = Organization
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Only show organization members (excluding current owner) as potential new owners
            self.fields['new_owner'].queryset = self.instance.users.exclude(id=self.instance.owner.id)
            self.fields['new_owner'].label = _("Transfer Ownership")
        else:
            # Hide the field for new organizations
            self.fields['new_owner'].widget = forms.HiddenInput()
