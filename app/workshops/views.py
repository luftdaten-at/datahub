import csv

from django.utils import timezone
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import HttpResponse, Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.core.mail import send_mail

from .models import Workshop, WorkshopInvitation
from .forms import WorkshopForm
from accounts.models import CustomUser
from api.models import AirQualityRecord
from main import settings


class WorkshopListView(ListView):
    model = Workshop
    context_object_name = 'workshops'
    template_name = 'workshops/list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Upcoming workshops: those with end_date in the future, sorted descending (latest first)
        upcoming_qs = Workshop.objects.filter(
            end_date__gt=timezone.now(), public=True
        ).order_by('-end_date')
        paginator_upcoming = Paginator(upcoming_qs, 10)
        page_upcoming = self.request.GET.get('page_upcoming')
        try:
            upcoming_page = paginator_upcoming.page(page_upcoming)
        except PageNotAnInteger:
            upcoming_page = paginator_upcoming.page(1)
        except EmptyPage:
            upcoming_page = paginator_upcoming.page(paginator_upcoming.num_pages)
        context['upcoming_workshops'] = upcoming_page

        # Past workshops: those with end_date in the past, sorted descending (most recent first)
        past_qs = Workshop.objects.filter(
            end_date__lte=timezone.now(), public=True
        ).order_by('-end_date')
        paginator_past = Paginator(past_qs, 10)
        page_past = self.request.GET.get('page_past')
        try:
            past_page = paginator_past.page(page_past)
        except PageNotAnInteger:
            past_page = paginator_past.page(1)
        except EmptyPage:
            past_page = paginator_past.page(paginator_past.num_pages)
        context['past_workshops'] = past_page
        
        return context


class WorkshopDetailView(DetailView):
    model = Workshop
    context_object_name = 'workshop'
    template_name = 'workshops/detail.html'

    # def get_queryset(self):
    #     """
    #     This method is overridden to only include workshops that are public.
    #     """
    #     return Workshop.objects.filter(public=True)
    
    def get_object(self, queryset=None):
        """
        This method is overridden to provide additional checks for the workshop's visibility.
        If the requested workshop is not public, it raises a 404.
        """
        try:
            queryset = self.get_queryset() if queryset is None else queryset
            obj = super().get_object(queryset=queryset)
        
        except Workshop.DoesNotExist:
            raise Http404("Workshop nicht gefunden.")
        
        if not obj.public:
            if not self.request.user.is_superuser and obj.owner != self.request.user:
                raise Http404("Workshop nicht gefunden.")

        return obj


@login_required
def invite_user_to_workshop(request, workshop_id):
    workshop = get_object_or_404(Workshop, name=workshop_id)
    email = request.POST.get('email')
    
    # Check permissions
    if not request.user.is_superuser and request.user != Workshop.owner:
        messages.error(request, "You do not have permission to invite users to this organization.")
        return redirect('workshop-detail', workshop.pk)

    user = CustomUser.objects.filter(email=email).first()

    if user:
        workshop.users.add(user)
        messages.success(request, f"{email} has been added to the organization.")
    else:
        # Check if invitation already exists
        invitation = WorkshopInvitation.objects.filter(email=email, workshop=workshop).first()

        if not invitation:
            # Create an invitation
            invitation = WorkshopInvitation(
                expiring_date=None,
                email=email,
                workshop=workshop,
            )
            invitation.save()

        # Generate the email body from a template
        context = {
            'workshop': workshop,
            'registration_link': ''
        }
        message_body = render_to_string('workshops/email/invite_user_to_workshop.txt', context)

        # Send the email
        send_mail(
            subject=f"You've been invited to join {workshop.name}",
            message=message_body,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
        )

        messages.success(request, f"An invitation has been sent to {email}.")

    return redirect('workshop-detail', workshop.pk)


class WorkshopMyView(LoginRequiredMixin, ListView):
    model = Workshop
    template_name = 'workshops/my.html'
    context_object_name = 'workshops'
    paginate_by = 10 

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Workshop.objects.filter().order_by('-end_date')
        else:
            return Workshop.objects.filter(owner=self.request.user).order_by('-end_date')


class WorkshopCreateView(CreateView):
    model = Workshop
    form_class = WorkshopForm
    template_name = 'workshops/form.html'
    success_url = reverse_lazy('workshops-my')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)
    

class WorkshopUpdateView(UpdateView):
    model = Workshop
    form_class = WorkshopForm
    template_name = 'workshops/form.html'

    def get_success_url(self):
        return reverse_lazy('workshops-my')

    def form_valid(self, form):
  
        return super().form_valid(form)
    

class WorkshopDeleteView(DeleteView):
    model = Workshop
    template_name = 'workshops/confirm_delete.html'
    success_url = reverse_lazy('workshops-my')

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(owner=self.request.user)
        return queryset
    

class WorkshopExportCsvView(View):
    def get(self, request, pk, *args, **kwargs):
        try:
            workshop = Workshop.objects.get(pk=pk)
        except Workshop.DoesNotExist:
            raise Http404("Workshop nicht gefunden.")

        if not workshop.public and workshop.owner != request.user:
            raise Http404("Workshop nicht gefunden.")

        records = AirQualityRecord.objects.filter(workshop__name=pk)

        # CSV-Antwort vorbereiten
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{workshop.name}_data.csv"'

        writer = csv.writer(response)
        header = ['id', 'time', 'pm1', 'pm25', 'pm10', 'temperature', 'humidity', 'device', 'participant', 'lat', 'lon', 'location_precision', 'mode']
        writer.writerow(header)

        for record in records:
            writer.writerow([
                record.id,
                record.time,
                record.pm1,
                record.pm25,
                record.pm10,
                record.temperature,
                record.humidity,
                record.device,
                record.participant,
                record.lat,
                record.lon,
                record.location_precision,
                record.mode
            ])

        return response