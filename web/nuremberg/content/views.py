from django.views.generic import TemplateView
from django.views.generic.detail import DetailView

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


class ReportDetailView(DetailView):

    model = AnalystReport
    template_name = 'content/report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for pos in ('next', 'previous'):
            try:
                context[pos] = getattr(self.object, f'get_{pos}_by_date')()
            except AnalystReport.DoesNotExist:
                context[pos] = None
        return context
