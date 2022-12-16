from django.urls import path
from . import views

app_name = 'search'
urlpatterns = [
    path('', views.Search.as_view(), name='search'),
    path('advanced', views.advanced_search, name='advanced-search'),
]
