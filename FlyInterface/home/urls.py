from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('projects/<path:root_path>', views.index, name='project-sites')
]