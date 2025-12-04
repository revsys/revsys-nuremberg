from django.http.response import JsonResponse
from django.template.loader import render_to_string
from django.shortcuts import render
from django.views.generic import View

from nuremberg.search.views import Search as GenericSearchView
from .models import Transcript
from .xml import TranscriptPageJoiner


class Search(GenericSearchView):
    template_name = 'transcripts/search.html'

    paginate_by = 10
    default_sort = 'page'

    def get(self, request, transcript_id, *args, **kwargs):
        self.transcript = Transcript.objects.get(id=transcript_id)
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'transcript_id': self.transcript.id})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {'transcript': self.transcript, 'show_search_bar': True}
        )
        return context


class Show(View):
    template_name = 'transcripts/show.html'
    page_alignment = 10

    def get(self, request, transcript_id, *args, **kwargs):
        transcript = Transcript.objects.get(id=transcript_id)
        total_pages = transcript.total_pages

        query = request.GET.get('q')
        seq_number = int(request.GET.get('seq', 1))
        # Note: 'page' parameter no longer supported, only 'seq'

        page_date = request.GET.get('date')
        if page_date:
            seq_number = transcript.get_seq_from_page_date(
                page_date, seq_number
            )

        from_seq, to_seq = self.get_request_seq_range(request, seq_number)

        from_seq = transcript.clamp_seq(from_seq)
        to_seq = transcript.clamp_seq(to_seq)

        pages = transcript.pages.filter(
            seq_number__gte=from_seq, seq_number__lte=to_seq
        ).all()
        joiner = TranscriptPageJoiner(
            pages,
            query=query,
            include_first=from_seq == 1,
            include_last=to_seq == total_pages,
        )
        joiner.build_html()

        context = {
            'html': render_to_string(
                'transcripts/joined_pages.html',
                {'pages': joiner.html_pages},
            ),
            'from_seq': joiner.from_seq,
            'to_seq': joiner.to_seq,
            'seq': seq_number,
        }

        if request.GET.get('partial'):
            return JsonResponse(context)

        current_page = next(
            page for page in pages if page.seq_number == seq_number
        )
        context.update(
            {
                'transcript': transcript,
                'total_pages': total_pages,
                'dates': transcript.dates(),
                'current_page': current_page,
                'query': query,
                'page_obj': None,
                'show_search_bar': False,
            }
        )
        return render(request, self.template_name, context)

    def get_request_seq_range(self, request, seq_number):
        # so that page ranges are generally cacheable, we align initial page loads to 10-page strides, plus 1
        # e.g. requesting seq=10, 13, or 19 will get you pages 1 - 30 inclusive,
        # so all future range requests will be aligned to 31 - 40 and so on.
        from_seq = int(
            request.GET.get(
                'from_seq',
                (seq_number // self.page_alignment) * self.page_alignment
                - self.page_alignment,
            )
        )
        to_seq = int(
            request.GET.get(
                'to_seq',
                (seq_number // self.page_alignment) * self.page_alignment
                + self.page_alignment
                + 1,
            )
        )

        return (from_seq, to_seq)
