import datetime
from django.urls import reverse_lazy
from django.views import generic
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm

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

def dashboard(request):
    """
    Display a dashboard overview for the logged-in account.
    If the user is not authenticated, display the login form.
    """
    if request.user.is_authenticated:
        # Here, you can add additional context for the dashboard as needed
        context = {
            'user': request.user,
            # add other variables for your dashboard here
        }
        return render(request, "account/dashboard.html", context)
    else:
        # Process the login form for unauthenticated users
        form = AuthenticationForm(request=request, data=request.POST or None)
        if request.method == "POST":
            if form.is_valid():
                user = form.get_user()
                login(request, user)
                return redirect("dashboard")  # Ensure 'dashboard' is named appropriately in your urls.py
        return render(request, "account/login.html", {"form": form})