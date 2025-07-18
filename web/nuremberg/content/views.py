from django.views.generic import TemplateView
from django.views.generic.detail import DetailView

from nuremberg.content.models import AnalystReport
from nuremberg.documents.models import DocumentCase


class ContentView(TemplateView):
    context = {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.context)
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        response.set_cookie("foobar", "normal", max_age=3600 * 24)
        return response


class LandingView(ContentView):
    template_name = "content/landing.html"
    context = {
        "query": "",
        "case": DocumentCase.objects.get(tag_name="IMT"),
        "reports": AnalystReport.objects.all(),
    }


class TrialsView(ContentView):
    template_name = "content/trials.html"
    context = {
        "cases": DocumentCase.objects.all().order_by("id"),
    }


class ReportDetailView(DetailView):
    model = AnalystReport
    template_name = "content/report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for pos in ("next", "previous"):
            try:
                context[pos] = getattr(self.object, f"get_{pos}_by_date")()
            except AnalystReport.DoesNotExist:
                context[pos] = None
        return context
