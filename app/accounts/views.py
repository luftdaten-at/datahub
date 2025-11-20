import datetime
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView
from django.views.generic.list import ListView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import AuthenticationForm, AdminPasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .forms import CustomUserCreationForm, CustomUserEditForm
from .models import CustomUser
from organizations.models import Organization, OrganizationInvitation
from workshops.models import Workshop, WorkshopInvitation
from campaign.models import Campaign


class AccountDeleteView(LoginRequiredMixin, DeleteView):
    model = CustomUser
    template_name = 'account/account_confirm_delete.html'
    success_url = reverse_lazy('home')

    def get_object(self, queryset=None):
        # Ensure that only the logged-in user can delete their account
        return self.request.user

    def delete(self, request, *args, **kwargs):
        # Optionally, add a message for the user or perform extra cleanup
        messages.success(request, "Your account has been deleted successfully.")
        return super().delete(request, *args, **kwargs)


def DashboardView(request):
    """
    Display a dashboard overview for the logged-in account.
    If the user is not authenticated, display the login form.
    """
    if request.user.is_authenticated:
        context = {
            'user': request.user,
            'member_campaigns': Campaign.objects.filter(users=request.user),
            'owner_campaigns': Campaign.objects.filter(owner=request.user),
            'member_organizations': Organization.objects.filter(users=request.user),
            'owner_organizations': Organization.objects.filter(owner=request.user),
        }

        context['campaigns'] = Campaign.objects.all() if request.user.is_superuser else context['member_campaigns']
        context['organizations'] = context['member_organizations'] if not request.user.is_superuser else Organization.objects.all()

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


class SignupPageView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("account_login")
    template_name = "account/signup.html"

    def form_valid(self, form):
        user = form.instance

        # Invitations to organizations
        invitations = OrganizationInvitation.objects.filter(email=user.email).all()
        time_now = datetime.datetime.now(datetime.timezone.utc)
        user.save()
        for invitation in invitations:
            if not invitation.expiring_date or time_now < invitation.expiring_date:
                invitation.organization.users.add(user)
            invitation.delete()
        
        # Invitations to workshops
        invitations = WorkshopInvitation.objects.filter(email=user.email).all()
        time_now = datetime.datetime.now(datetime.timezone.utc)
        user.save()
        for invitation in invitations:
            if not invitation.expiring_date or time_now < invitation.expiring_date:
                invitation.workshop.users.add(user)
            invitation.delete()

        return super().form_valid(form)


def SettingsView(request):
    """
    Display a dashboard overview for the logged-in account.
    If the user is not authenticated, display the login form.
    """
    if request.user.is_authenticated:
        print(request.user.measurements.count())
        # Here, you can add additional context for the dashboard as needed
        context = {
            'user': request.user,
            # add other variables for your dashboard here
        }
        return render(request, "account/settings.html", context)
    else:
        # Process the login form for unauthenticated users
        form = AuthenticationForm(request=request, data=request.POST or None)
        if request.method == "POST":
            if form.is_valid():
                user = form.get_user()
                login(request, user)
                return redirect("settings")
        return render(request, "account/login.html", {"form": form})
    

class DataDeleteView(TemplateView, LoginRequiredMixin):
    template_name = 'account/data_confirm_delete.html'

    def post(self, request, *args, **kwargs):
        # delete all data that corresponds to the logged in user
        user = self.request.user
        user.measurements.all().delete()
        messages.success(request, 'All Data that belongs to your account has been deleted')

        return redirect('settings')


class UsersUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = get_user_model()
    form_class = CustomUserEditForm
    template_name = 'account/users/edit.html'
    pk_url_kwarg = 'user_id'  # Erwartet in der URL: /users/edit/<user_id>/

    def get_success_url(self):
        return reverse_lazy('users-list')

    def test_func(self):
        # Zugriff erlauben, wenn der angemeldete Benutzer ein Superuser ist
        return self.request.user.is_superuser


class UsersListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CustomUser
    context_object_name = 'users'
    template_name = 'account/users/list.html'

    def test_func(self):
        # Only superusers can access this view
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_queryset(self):
        # Optimize queryset by selecting related 'current_organization'
        return CustomUser.objects.all().order_by('id')


class UserPasswordChangeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """View for superusers to change user passwords."""
    template_name = 'account/users/password_change.html'
    form_class = AdminPasswordChangeForm

    def test_func(self):
        # Only superusers can access this view
        return self.request.user.is_superuser

    def get_user(self):
        """Get the user whose password is being changed."""
        user_id = self.kwargs.get('user_id')
        return get_user_model().objects.get(pk=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_user()
        context['target_user'] = user
        if self.request.method == 'POST':
            context['form'] = self.form_class(user, self.request.POST)
        else:
            context['form'] = self.form_class(user)
        return context

    def post(self, request, *args, **kwargs):
        user = self.get_user()
        form = self.form_class(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Password for {user.username} has been changed successfully.")
            return redirect('users-list')
        return self.render_to_response(self.get_context_data(form=form))
