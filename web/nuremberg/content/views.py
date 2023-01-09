from django.views.generic import TemplateView

from nuremberg.content.models import AnalystReport


class ContentView(TemplateView):
    context = {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.context)
        return context


class LandingView(ContentView):

    template_name = 'content/landing.html'
    context = {'query': '', 'reports': AnalystReport.objects.all()}
