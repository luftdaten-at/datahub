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
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils import translation
import logging

from main import settings
from accounts.models import CustomUser
from organizations.models import Organization, OrganizationInvitation
from organizations.forms import OrganizationForm

logger = logging.getLogger(__name__)


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

    def form_valid(self, form):
        organization = form.save(commit=False)
        new_owner = form.cleaned_data.get('new_owner')
        
        if new_owner and new_owner != organization.owner:
            # Transfer ownership
            old_owner = organization.owner
            organization.owner = new_owner
            organization.save()
            
            # Add success message
            messages.success(
                self.request, 
                f"Ownership of '{organization.name}' has been transferred from {old_owner.username} to {new_owner.username}."
            )
        else:
            # Just save the organization without ownership change
            organization.save()
            messages.success(self.request, f"Organization '{organization.name}' has been updated successfully.")
        
        return super().form_valid(form)


class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = 'organizations/detail.html'
    context_object_name = 'organization'

    def get_success_url(self):
        # and 'self.object.pk' with the primary key of the newly created object
        return reverse_lazy('organizations-my', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add pending invitations to the context
        context['pending_invitations'] = OrganizationInvitation.objects.filter(
            organization=self.object
        ).order_by('-id')
        return context
    
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
    if not request.user.is_superuser and request.user != organization.owner:
        messages.error(request, "You do not have permission to remove users from this organization.")
        return redirect('organizations-detail', pk=org_id)
    
    # the owner cannot be removed
    if user == organization.owner:
        messages.error(request, "The Owner of the Organization cannot be removed")
        return redirect('organizations-detail', pk=org_id)

    organization.users.remove(user)
    return redirect('organizations-detail', pk=org_id)


@login_required
def invite_user_to_organization(request, org_id):
    if request.method != 'POST':
        return redirect("organizations-detail", pk=org_id)

    organization = get_object_or_404(Organization, id=org_id)
    email = request.POST.get('email')
    
    logger.info(f"User {request.user.username} attempting to invite {email} to organization {organization.name}")
    
    # Check permissions
    if not request.user.is_superuser and request.user != organization.owner:
        logger.warning(f"User {request.user.username} denied permission to invite users to organization {organization.name}")
        messages.error(request, "You do not have permission to invite users to this organization.")
        return redirect("organizations-detail", pk=org_id)

    if not email:
        logger.warning(f"Empty email provided for invitation to organization {organization.name}")
        messages.error(request, "Please provide a valid email address.")
        return redirect("organizations-detail", pk=org_id)

    user = CustomUser.objects.filter(email=email).first()

    # Check if user is already a member
    if user and organization.users.filter(id=user.id).exists():
        logger.info(f"User {email} is already a member of organization {organization.name}")
        messages.info(request, f"{email} is already a member of this organization.")
        return redirect("organizations-detail", pk=org_id)

    # Check if invitation already exists
    invitation = OrganizationInvitation.objects.filter(email=email, organization=organization).first()

    if not invitation:
        # Create an invitation
        invitation = OrganizationInvitation(
            expiring_date=None,
            email=email,
            organization=organization,
        )
        invitation.save()
        logger.info(f"Created new invitation for {email} to organization {organization.name}")
    else:
        logger.info(f"Invitation already exists for {email} to organization {organization.name}")

    # Generate the email body from a template
    current_language = translation.get_language()
    
    if user:
        # Existing user - send direct join link
        join_link = request.build_absolute_uri(f'/organizations/{organization.pk}/accept-invitation/{invitation.pk}/')
        context = {
            'organization': organization,
            'join_link': join_link,
            'is_existing_user': True
        }
        logger.info(f"Sending invitation email to existing user {email} for organization {organization.name}")
    else:
        # New user - send registration link
        registration_link = request.build_absolute_uri('/accounts/signup/')
        context = {
            'organization': organization,
            'registration_link': registration_link,
            'is_existing_user': False
        }
        logger.info(f"Sending invitation email to new user {email} for organization {organization.name}")

    # Try to use localized template first, fall back to default
    template_paths = [
        f'organizations/email/{current_language}/invite_user_to_organization.txt',
        'organizations/email/invite_user_to_organization.txt'
    ]
    
    message_body = None
    for template_path in template_paths:
        try:
            message_body = render_to_string(template_path, context, request=request)
            break
        except:
            continue
    
    if not message_body:
        message_body = render_to_string('organizations/email/invite_user_to_organization.txt', context, request=request)

    # Localized subject
    if current_language == 'de':
        subject = f"Sie wurden eingeladen, {organization.name} beizutreten"
    else:
        subject = f"You've been invited to join {organization.name}"

    try:
        # Send the email
        send_mail(
            subject=subject,
            message=message_body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER),
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"Invitation email sent successfully to {email} for organization {organization.name} in language {current_language}")
        messages.success(request, f"An invitation has been sent to {email}.")
    except Exception as e:
        logger.error(f"Failed to send invitation email to {email} for organization {organization.name}: {str(e)}")
        messages.error(request, f"Failed to send invitation email to {email}. Please try again later.")

    return redirect("organizations-detail", pk=org_id)


@login_required
def accept_invitation(request, org_id, invitation_id):
    organization = get_object_or_404(Organization, id=org_id)
    invitation = get_object_or_404(OrganizationInvitation, id=invitation_id, organization=organization)
    
    logger.info(f"User {request.user.username} attempting to accept invitation {invitation_id} for organization {organization.name}")
    
    # Check if the invitation email matches the current user's email
    if request.user.email != invitation.email:
        logger.warning(f"User {request.user.username} email mismatch for invitation {invitation_id}")
        messages.error(request, "This invitation is not for your email address.")
        return redirect("organizations-my")
    
    # Check if user is already a member
    if organization.users.filter(id=request.user.id).exists():
        logger.info(f"User {request.user.username} is already a member of organization {organization.name}")
        messages.info(request, f"You are already a member of {organization.name}.")
        # Delete the invitation since user is already a member
        invitation.delete()
        return redirect("organizations-detail", pk=org_id)
    
    try:
        # Add user to organization
        organization.users.add(request.user)
        # Delete the invitation
        invitation.delete()
        logger.info(f"User {request.user.username} successfully joined organization {organization.name}")
        messages.success(request, f"You have successfully joined {organization.name}!")
    except Exception as e:
        logger.error(f"Failed to add user {request.user.username} to organization {organization.name}: {str(e)}")
        messages.error(request, "Failed to join the organization. Please try again.")
    
    return redirect("organizations-detail", pk=org_id)


@login_required
def cancel_invitation(request, org_id, invitation_id):
    organization = get_object_or_404(Organization, id=org_id)
    invitation = get_object_or_404(OrganizationInvitation, id=invitation_id, organization=organization)
    
    logger.info(f"User {request.user.username} attempting to cancel invitation {invitation_id} for {invitation.email} in organization {organization.name}")
    
    # Check permissions
    if not request.user.is_superuser and request.user != organization.owner:
        logger.warning(f"User {request.user.username} denied permission to cancel invitation in organization {organization.name}")
        messages.error(request, "You do not have permission to cancel invitations for this organization.")
        return redirect("organizations-detail", pk=org_id)
    
    try:
        invitation.delete()
        logger.info(f"Invitation {invitation_id} for {invitation.email} cancelled successfully")
        messages.success(request, f"Invitation for {invitation.email} has been cancelled.")
    except Exception as e:
        logger.error(f"Failed to cancel invitation {invitation_id}: {str(e)}")
        messages.error(request, "Failed to cancel invitation. Please try again.")
    
    return redirect("organizations-detail", pk=org_id)


@login_required
def resend_invitation(request, org_id, invitation_id):
    organization = get_object_or_404(Organization, id=org_id)
    invitation = get_object_or_404(OrganizationInvitation, id=invitation_id, organization=organization)
    
    logger.info(f"User {request.user.username} attempting to resend invitation {invitation_id} for {invitation.email} in organization {organization.name}")
    
    # Check permissions
    if not request.user.is_superuser and request.user != organization.owner:
        logger.warning(f"User {request.user.username} denied permission to resend invitation in organization {organization.name}")
        messages.error(request, "You do not have permission to resend invitations for this organization.")
        return redirect("organizations-detail", pk=org_id)
    
    email = invitation.email
    user = CustomUser.objects.filter(email=email).first()
    
    # Generate the email body from a template
    current_language = translation.get_language()
    
    if user:
        # Existing user - send direct join link
        join_link = request.build_absolute_uri(f'/organizations/{organization.pk}/accept-invitation/{invitation.pk}/')
        context = {
            'organization': organization,
            'join_link': join_link,
            'is_existing_user': True
        }
        logger.info(f"Resending invitation email to existing user {email} for organization {organization.name}")
    else:
        # New user - send registration link
        registration_link = request.build_absolute_uri('/accounts/signup/')
        context = {
            'organization': organization,
            'registration_link': registration_link,
            'is_existing_user': False
        }
        logger.info(f"Resending invitation email to new user {email} for organization {organization.name}")

    # Try to use localized template first, fall back to default
    template_paths = [
        f'organizations/email/{current_language}/invite_user_to_organization.txt',
        'organizations/email/invite_user_to_organization.txt'
    ]
    
    message_body = None
    for template_path in template_paths:
        try:
            message_body = render_to_string(template_path, context, request=request)
            break
        except:
            continue
    
    if not message_body:
        message_body = render_to_string('organizations/email/invite_user_to_organization.txt', context, request=request)

    # Localized subject
    if current_language == 'de':
        subject = f"Sie wurden eingeladen, {organization.name} beizutreten"
    else:
        subject = f"You've been invited to join {organization.name}"

    try:
        # Send the email
        send_mail(
            subject=subject,
            message=message_body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER),
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"Invitation email resent successfully to {email} for organization {organization.name} in language {current_language}")
        messages.success(request, f"Invitation has been resent to {email}.")
    except Exception as e:
        logger.error(f"Failed to resend invitation email to {email} for organization {organization.name}: {str(e)}")
        messages.error(request, f"Failed to resend invitation email to {email}. Please try again later.")
    
    return redirect("organizations-detail", pk=org_id)