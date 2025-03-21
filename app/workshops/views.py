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

from .models import Workshop
from .forms import WorkshopForm
from api.models import AirQualityRecord

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

    def get_queryset(self):
        """
        This method is overridden to only include workshops that are public.
        """
        # Only fetch workshops that are public.
        return Workshop.objects.filter(public=True)
    
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

        if not obj.public and obj.owner != self.request.user:
            raise Http404("Workshop nicht gefunden.")

        return obj


class WorkshopMyView(LoginRequiredMixin, ListView):
    model = Workshop
    template_name = 'workshops/my.html'
    context_object_name = 'workshops'
    
    def get_queryset(self):
        if self.request.user.is_superuser:  # Check if the user is an admin
            return Workshop.objects.all()  # Admin sees all workshops
        else:
            return Workshop.objects.filter(owner=self.request.user)  # Filter by owner


class WorkshopCreateView(CreateView):
    model = Workshop
    form_class = WorkshopForm
    template_name = 'workshops/form.html'
    success_url = reverse_lazy('workshops-my')  # Redirect after a successful creation

    def form_valid(self, form):
        form.instance.owner = self.request.user  # Set the owner to the current user
        return super().form_valid(form)
    

class WorkshopUpdateView(UpdateView):
    model = Workshop
    form_class = WorkshopForm
    template_name = 'workshops/form.html'  # Reuse the form template

    def get_success_url(self):
        return reverse_lazy('workshops-my')  # Redirect to the workshop list after update

    def form_valid(self, form):
  
        return super().form_valid(form)
    

class WorkshopDeleteView(DeleteView):
    model = Workshop
    template_name = 'workshops/confirm_delete.html'  # Confirmation page template
    success_url = reverse_lazy('workshops-my')  # Redirect here after deletion

    def get_queryset(self):
        queryset = super().get_queryset()
        # Optional: restrict deletion to the owner or admin
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
        # Header: Dynamisch alle Feldnamen des Models abrufen
        field_names = [field.name for field in AirQualityRecord._meta.fields]
        writer.writerow(field_names)

        # Für jeden Record werden die Werte der Felder als Zeile in die CSV geschrieben
        for record in records:
            writer.writerow([getattr(record, field) for field in field_names])

        return response