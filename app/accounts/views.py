import datetime
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.list import ListView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import AuthenticationForm, AdminPasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .forms import CustomUserCreationForm, CustomUserEditForm
from .models import CustomUser
from organizations.models import OrganizationInvitation
from workshops.models import Workshop, WorkshopInvitation
from municipalities.models import FavoriteMunicipality
from stations.models import FavoriteStation

from .dashboard_air import (
    build_favorite_municipality_rows,
    build_favorite_station_rows,
)


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
        favorite_municipalities = FavoriteMunicipality.objects.filter(
            user=request.user
        )
        favorite_stations = FavoriteStation.objects.filter(user=request.user)
        context = {
            "user": request.user,
            "favorite_municipality_rows": build_favorite_municipality_rows(
                favorite_municipalities
            ),
            "favorite_station_rows": build_favorite_station_rows(favorite_stations),
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
        return reverse_lazy('users-edit', kwargs={'user_id': self.object.pk})

    def test_func(self):
        # Zugriff erlauben, wenn der angemeldete Benutzer ein Superuser ist
        return self.request.user.is_superuser

    def form_valid(self, form):
        messages.success(self.request, _('Profile has been saved.'))
        return super().form_valid(form)


class UsersPermissionUpdateView(LoginRequiredMixin, UserPassesTestMixin, SingleObjectMixin, View):
    """POST-only toggles for is_active (reactivate only), is_staff, is_superuser."""

    model = get_user_model()
    pk_url_kwarg = 'user_id'
    http_method_names = ['post']
    _ALLOWED_FLAGS = frozenset({'is_active', 'is_staff', 'is_superuser'})

    def test_func(self):
        return self.request.user.is_superuser

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        flag = request.POST.get('flag')
        if flag not in self._ALLOWED_FLAGS:
            messages.error(request, _('Invalid permission field.'))
            return redirect('users-edit', user_id=self.object.pk)

        set_to = request.POST.get('set_to') == '1'

        if flag == 'is_active':
            if set_to:
                self.object.is_active = True
                self.object.save(update_fields=['is_active'])
                messages.success(request, _('The account can log in again.'))
            else:
                messages.info(
                    request,
                    _(
                        'Use “Deactivate account” below to turn off login '
                        '(with confirmation).'
                    ),
                )
            return redirect('users-edit', user_id=self.object.pk)

        if flag == 'is_staff':
            self.object.is_staff = set_to
            self.object.save(update_fields=['is_staff'])
            if set_to:
                messages.success(request, _('Staff access has been granted.'))
            else:
                messages.success(request, _('Staff access has been revoked.'))
            return redirect('users-edit', user_id=self.object.pk)

        if flag == 'is_superuser':
            if not set_to and self.object.is_superuser:
                if not (
                    get_user_model()
                    .objects.filter(is_superuser=True)
                    .exclude(pk=self.object.pk)
                    .exists()
                ):
                    messages.error(
                        request,
                        _('You cannot remove the only remaining superuser.'),
                    )
                    return redirect('users-edit', user_id=self.object.pk)
            self.object.is_superuser = set_to
            self.object.save(update_fields=['is_superuser'])
            if set_to:
                messages.success(request, _('Superuser privileges have been granted.'))
            else:
                messages.success(request, _('Superuser privileges have been revoked.'))
            return redirect('users-edit', user_id=self.object.pk)

        return redirect('users-edit', user_id=self.object.pk)


class UsersDeactivateView(LoginRequiredMixin, UserPassesTestMixin, SingleObjectMixin, View):
    """Set is_active=False so the user can no longer log in (superuser-only)."""

    model = get_user_model()
    pk_url_kwarg = 'user_id'

    def test_func(self):
        return self.request.user.is_superuser

    def _deactivate_guard_redirect(self, obj):
        if obj.pk == self.request.user.pk:
            messages.error(
                self.request,
                _('You cannot deactivate your own account from user management.'),
            )
            return redirect('users-list')
        if not obj.is_active:
            messages.info(
                self.request,
                _('This user is already inactive.'),
            )
            return redirect('users-edit', user_id=obj.pk)
        if obj.is_superuser and not (
            get_user_model()
            .objects.filter(is_superuser=True)
            .exclude(pk=obj.pk)
            .exists()
        ):
            messages.error(
                self.request,
                _('You cannot deactivate the only remaining superuser.'),
            )
            return redirect('users-edit', user_id=obj.pk)
        return None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        guard = self._deactivate_guard_redirect(self.object)
        if guard is not None:
            return guard
        return render(
            request,
            'account/users/confirm_deactivate.html',
            {'object': self.object},
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        guard = self._deactivate_guard_redirect(self.object)
        if guard is not None:
            return guard
        username = self.object.get_username()
        self.object.is_active = False
        self.object.save(update_fields=['is_active'])
        messages.success(
            request,
            _('User "%(name)s" has been deactivated.') % {'name': username},
        )
        return redirect('users-edit', user_id=self.object.pk)


class UsersListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CustomUser
    context_object_name = 'users'
    template_name = 'account/users/list.html'
    paginate_by = 50

    def test_func(self):
        # Only superusers can access this view
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_queryset(self):
        return CustomUser.objects.filter(is_active=True).order_by('id')


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
            messages.success(
                request,
                _('Password for %(username)s has been changed successfully.')
                % {'username': user.username},
            )
            return redirect('users-edit', user_id=user.pk)
        return self.render_to_response(self.get_context_data(form=form))
