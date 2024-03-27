from django.views.generic import TemplateView


class HomePageView(TemplateView):
    template_name = "home.html"

class ArbeitsplatzView(TemplateView):
    template_name = "arbeitsplatz.html"