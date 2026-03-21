from django import forms

from .models import FAQEntry


class FAQEntryStaffForm(forms.ModelForm):
    class Meta:
        model = FAQEntry
        fields = ("question", "answer", "is_published")
