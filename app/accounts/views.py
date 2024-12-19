import datetime
from django.urls import reverse_lazy
from django.views import generic

from .forms import CustomUserCreationForm
from campaign.models import OrganizationInvitation


class SignupPageView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("account_login")
    template_name = "account/signup.html"

    def form_valid(self, form):
        print('form_valid called')
        return super().form_valid(form)

    def form_invalid(self, form):
        print('form_invalid called')
        print(form.errors)
        return super().form_invalid(form)
