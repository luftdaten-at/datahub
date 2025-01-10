from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied

from main import settings
from accounts.models import CustomUser
from organizations.models import Organization, OrganizationInvitation
from organizations.forms import OrganizationForm


class OrganizationsView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = 'organizations/my.html'
    context_object_name = 'owned_organizations'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add organizations where the user is a member
        context['member_organizations'] = Organization.objects.filter(users=self.request.user)
        context['owner_organizations'] = Organization.objects.filter(owner=self.request.user)
        context['organizations'] = context['member_organizations'] if not self.request.user.is_superuser else Organization.objects.all()

        return context


class OrganizationCreateView(LoginRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'organizations/create.html'
    success_url = reverse_lazy('organizations-my')  # Redirect to a list view or another page

    def form_valid(self, form):
        # Check if the user already owns any organizations
        if self.request.user.owned_organizations.exists():
            messages.error(self.request, "You already own an organization and cannot create another one.")
            return super().form_invalid(form)
        
        # Set the current user as the owner of the organization
        organization = form.save(commit=False)
        organization.owner = self.request.user
        organization.save()
        organization.users.add(self.request.user)
        organization.save()

        return super().form_valid(form)


class OrganizationUpdateView(LoginRequiredMixin, UpdateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'organizations/create.html'
    success_url = reverse_lazy('organizations-my')  # Redirect to a list view or another page

    def get_object(self, queryset = None):
        organisation = super().get_object(queryset)
        if self.request.user.is_superuser:
            return organisation
        if self.request.user != organisation.owner:
            raise PermissionDenied('You are not allowed to edite this Organization')
        return organisation


class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = 'organizations/detail.html'
    context_object_name = 'organization'

    def get_success_url(self):
        # and 'self.object.pk' with the primary key of the newly created object
        return reverse_lazy('organizations-my', kwargs={'pk': self.object.pk})
    
    
    def get_object(self, queryset = None): 
        organization = super().get_object(queryset)
        if self.request.user.is_superuser:
            return organization
        if not organization.users.filter(id=self.request.user.id).exists():
            raise PermissionDenied("Only members can view this Organization")
        return organization


class OrganizationDeleteView(LoginRequiredMixin, DeleteView):
    model = Organization
    template_name = 'organizations/confirm_delete.html'
    success_url = reverse_lazy('organizations-my')

    def get_object(self, queryset = None): 
        organization = super().get_object(queryset) 
        if self.request.user.is_superuser:
            return organization
        if self.request.user != organization.owner:
            raise PermissionDenied('You are not allowd to delete this Organization')
        return organization


@login_required
def remove_user_from_organization(request, org_id, user_id):
    organization = get_object_or_404(Organization, id=org_id)
    user = get_object_or_404(CustomUser, id=user_id)

    # Ensure the user performing the action has permission
    if request.user != organization.owner:
        messages.error(request, "You do not have permission to remove users from this organization.")
        return redirect('organizations-detail', pk=org_id)
    
    # the owner cannot be removed
    if user == request.user:
        messages.error(request, "The Owner of the Organization cannot be removed")
        return redirect('organizations-detail', pk=org_id)

    organization.users.remove(user)
    return redirect('organizations-detail', pk=org_id)


@login_required
def invite_user_to_organization(request, org_id):
    if request.method != 'POST':
        return redirect(f"organizations-detail", pk=org_id)

    organization = get_object_or_404(Organization, id=org_id)
    email = request.POST.get('email')
    
    if request.user != organization.owner:
        messages.error(request, "You do not have permission to invite users to this organization.")
        return redirect(f"organizations-detail", pk=org_id)

    user = CustomUser.objects.filter(email = email).first()

    if user:
        organization.users.add(user)
    else:
        # check if invitation already exists
        invitation = OrganizationInvitation.objects.filter(email=email, organization__pk = organization.pk).first()
        if invitation == None:
            # create invitation
            invitation = OrganizationInvitation(
                expiring_date = None,
                email = email,
                organization = organization,
            )
        invitation.save()
        # send invitation email
        # TODO add link to register
        send_mail(
            subject=f"You've been invited to join {organization.name}",
            message=f"Visit this link to register and join {organization.name}: <registration_link>",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
        )
        messages.success(request, f"An invitation has been sent to {email}.")

    return redirect(f"organizations-detail", pk=org_id)
