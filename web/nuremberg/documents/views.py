from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import View

from nuremberg.core.highlighter import NurembergHighlighter
from .models import Document, DocumentPersonalAuthor, DocumentText


class Show(View):
    template_name = 'documents/show.html'

    def highlight_query(self, text, query):
        return NurembergHighlighter(query).highlight(text)

    def get(self, request, document_id, *args, **kwargs):
        mode = request.GET.get('mode', 'image')
        query = request.GET.get('q')

        if mode == 'text':
            full_text = get_object_or_404(DocumentText, id=document_id)
            document = full_text.documents().first()
            evidence_codes = [full_text.evidence_code]
            if document is None:
                # For texts without a matching document, ignore `HLSL Item No.`
                document = full_text
                hlsl_item_id = None
            else:
                hlsl_item_id = document.id
            if query:
                full_text.text = self.highlight_query(full_text.text, query)
        else:
            document = get_object_or_404(
                Document.objects.prefetch_related(
                    'activities',
                    'cases',
                    'citations',
                    'evidence_codes',
                    'evidence_codes__prefix',
                    'exhibit_codes',
                    'images',
                ).select_related('language', 'source'),
                id=document_id,
            )
            full_text = document.full_texts().first()
            evidence_codes = document.evidence_codes.all()
            hlsl_item_id = document_id
            exhibit_codes = document.exhibit_codes.all()

        print("CODES!!!")
        print(exhibit_codes)
        print(exhibit_codes[0].pk)
        return render(
            request,
            self.template_name,
            {
                'document': document,
                'full_text': full_text,
                'hlsl_item_id': hlsl_item_id,
                'mode': mode,
                'evidence_codes': evidence_codes,
                'exhibit_codes': exhibit_codes,
                'citations': [
                    c for c in document.citations.all() if c.transcript_link
                ],
                'query': query,
            },
        )


def author_properties(request, author_id, author_slug=None):
    author = get_object_or_404(DocumentPersonalAuthor, id=author_id)
    result = author.metadata(backfill=True)

    if request.accepts('text/html'):
        response = render(request, 'documents/author.html', result)
    else:
        response = JsonResponse(data=result)

    return response
