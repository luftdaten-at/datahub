import datetime
from django.urls import reverse_lazy
from django.views import generic

from .forms import CustomUserCreationForm
from campaign.models import OrganizationInvitation


class SignupPageView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"

    def handle_post_registration(self, user):
        # search for pending invitations
        pending_invitations = OrganizationInvitation.objects.filter(email = user.email).all()
        for invitation in pending_invitations:
            # check if not already expired
            if invitation.expiring_date > datetime.datetime.now():
                invitation.organization.users.add(user)
            # delete invitation
            invitation.delete()
