import datetime
from django.urls import reverse_lazy
from django.views import generic

from .forms import CustomUserCreationForm
from organizations.models import OrganizationInvitation


class SignupPageView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("account_login")
    template_name = "account/signup.html"

    def form_valid(self, form):
        user = form.instance
        invitations = OrganizationInvitation.objects.filter(email=user.email).all()
        time_now = datetime.datetime.now(datetime.timezone.utc)
        user.save()
        for invitation in invitations:
            if not invitation.expiring_date or time_now < invitation.expiring_date:
                invitation.organization.users.add(user)
            invitation.delete()
        return super().form_valid(form)
