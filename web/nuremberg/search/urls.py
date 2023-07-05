from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = 'search'
urlpatterns = [
    path('', views.NewSearch.as_view(), name='search'),
    path('advanced', views.advanced_search, name='advanced'),
    path(
        'help',
        TemplateView.as_view(template_name='search/advanced-search-help.html'),
        name='help',
    ),
    path('old-search', views.Search.as_view(), name='old-search'),
    path('new-search', views.NewSearch.as_view(), name='new-search'),
]
