from django.views.generic import TemplateView

from main.settings import API_URL


class HelpPageView(TemplateView):
    template_name = "help.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['host'] = self.request.get_host()
        return context


class HomePageView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['host'] = self.request.get_host()
        context['API_URL'] = API_URL
        return context


class DocumentationPageView(TemplateView):
    template_name = "documentation.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['host'] = self.request.get_host()
        return context
