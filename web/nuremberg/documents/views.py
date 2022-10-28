from django.shortcuts import render
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


def author_properties(request, author_name):
    # XXX: Using the author name as author key could be flaky. Though currently
    # author names are reasonable "unique", we can't guarantee this condition.
    # But, in order to obtain an author ID, we should change the document
    # search indexes so they also store author ID in addition to author name,
    # and then return both in the search response.
    result = DocumentPersonalAuthor.objects.properties_by_author_name(
        author_name
    )

    if request.accepts('text/html'):
        response = render(request, 'documents/author.html', result)
    else:
        response = JsonResponse(data=result)

    return response
