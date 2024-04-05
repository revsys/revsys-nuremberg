from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, re_path

from .views import redirect_home

urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^transcripts/', include('nuremberg.transcripts.urls')),
    re_path(r'^documents/', include('nuremberg.documents.urls')),
    re_path(r'^photographs/', include('nuremberg.photographs.urls')),
    re_path(r'^search/', include('nuremberg.search.urls')),
    re_path(r'^', include('nuremberg.content.urls')),
    re_path(
        r'^robots.txt$',
        lambda r: HttpResponse(
            "User-agent: *\nDisallow: /search/", content_type="text/plain"
        ),
    ),
    re_path(r'^php', redirect_home),
]

# This helper function works ONLY in debug mode and ONLY if the given prefix
# is local (e.g. media/) and not a URL (e.g. http://media.example.com/).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = 'nuremberg.core.views.handler400'
handler403 = 'nuremberg.core.views.handler403'
handler404 = 'nuremberg.core.views.handler404'
handler500 = 'nuremberg.core.views.handler500'
