from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import View
from haystack.utils import Highlighter

from .models import Document, DocumentPersonalAuthor, DocumentText


class DocumentHighlighter(Highlighter):
    def find_window(self, highlight_locations):
        # Do not truncate the text at all -- show everything, from start to end
        return (0, len(self.text_block))


class Show(View):
    template_name = 'documents/show.html'

    def get_document(self, document_id):
        document = (
            Document.objects.prefetch_related(
                'activities', 'evidence_codes', 'exhibit_codes', 'images'
            )
            .select_related('language')
            .select_related('source')
            .get(id=document_id)
        )
        return document

    def get_full_text(self, text_id):
        full_text = DocumentText.objects.get(id=text_id)
        return full_text

    def highlight_query(self, text, query):
        highlight = DocumentHighlighter(query, html_tag='mark')
        return highlight.highlight(text)

    def get(self, request, document_id, *args, **kwargs):
        mode = request.GET.get('mode', 'image')
        query = request.GET.get('q')

        if mode == 'text':
            full_text = self.get_full_text(document_id)
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
            document = self.get_document(document_id)
            full_text = document.full_texts().first()
            evidence_codes = document.evidence_codes.all()
            hlsl_item_id = document_id

        return render(
            request,
            self.template_name,
            {
                'document': document,
                'full_text': full_text,
                'hlsl_item_id': hlsl_item_id,
                'mode': mode,
                'evidence_codes': evidence_codes,
                'query': query,
            },
        )


def author_properties(request, author_id, author_slug=None):
    author = get_object_or_404(DocumentPersonalAuthor, id=author_id)
    result = author.metadata()

    if request.accepts('text/html'):
        response = render(request, 'documents/author.html', result)
    else:
        response = JsonResponse(data=result)

    return response
