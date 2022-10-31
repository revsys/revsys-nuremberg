from django.urls import path, re_path
from . import views

app_name = 'documents'
urlpatterns = [
    re_path(
        r'^(?P<document_id>\d+)-(?P<slug>[-\w]+)?$',
        views.Show.as_view(),
        name='show',
    ),
    re_path(r'^(?P<document_id>\d+)[-\w]*$', views.Show.as_view()),
    path(
        'authors/<int:author_id>-<str:author_slug>',
        views.author_properties,
        name='author',
    ),
    path('authors/<int:author_id>', views.author_properties, name='author'),
]
