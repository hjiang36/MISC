from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('projects/<path:root_path>', views.index, name='project-sites'),
    path('viewer/<path:file_path>', views.imagej_viewer, name="imagej-viewer")
]