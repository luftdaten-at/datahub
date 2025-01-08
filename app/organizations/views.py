import statistics

from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail

from main import settings
from accounts.models import CustomUser
from organizations.models import Organization, OrganizationInvitation


class OrganizationsView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = 'campaigns/my_organizations.html'
    context_object_name = 'owned_organizations'

    def get_queryset(self):
        # Return organizations where the user is the owner
        return Organization.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add organizations where the user is a member
        context['member_organizations'] = Organization.objects.filter(users=self.request.user)
        return context


class OrganizationCreateView(LoginRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'campaigns/create_organization.html'
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

        # Add the user to the organization as a member
        organization.users.add(self.request.user)
        form.save_m2m()  # Save many-to-many relationships

        return super().form_valid(form)


class OrganizationDetailView(DetailView):
    model = Organization
    template_name = 'campaigns/organization_detail.html'
    context_object_name = 'organization'

    def get_success_url(self):
        # and 'self.object.pk' with the primary key of the newly created object
        return reverse_lazy('organizations-my', kwargs={'pk': self.object.pk})


@login_required
def remove_user_from_organization(request, org_id, user_id):
    organization = get_object_or_404(Organization, id=org_id)
    user = get_object_or_404(CustomUser, id=user_id)

    # Ensure the user performing the action has permission
    if request.user != organization.owner:
        messages.error(request, "You do not have permission to remove users from this organization.")
        return redirect('organization-detail', pk=org_id)

    organization.users.remove(user)
    messages.success(request, f"User {user.username} has been removed.")
    return redirect('organization-detail', pk=org_id)


@login_required
def invite_user_to_organization(request, org_id):
    if request.method != 'POST':
        return redirect(f"organization-detail", pk=org_id)

    organization = get_object_or_404(Organization, id=org_id)
    email = request.POST.get('email')
    
    if request.user != organization.owner:
        messages.error(request, "You do not have permission to invite users to this organization.")
        return redirect(f"organization-detail", pk=org_id)

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

    return redirect(f"organization-detail", pk=org_id)
