from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.views.generic import View

from .models import Document, DocumentPersonalAuthor


class Show(View):
    template_name = 'documents/show.html'

    def get(self, request, document_id, *args, **kwargs):
        document = (
            Document.objects.prefetch_related('images')
            .select_related('language')
            .select_related('source')
            .get(id=document_id)
        )

        return render(
            request,
            self.template_name,
            {'document': document, 'query': request.GET.get('q')},
        )


def author_properties(request, author_id, author_slug=None):
    author = get_object_or_404(DocumentPersonalAuthor, id=author_id)
    result = author.metadata()

    if request.accepts('text/html'):
        response = render(request, 'documents/author.html', result)
    else:
        response = JsonResponse(data=result)

    return response
