from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.urls import reverse

from .models import FwContextInfo

import flywheel
import os
import pathlib

# Retrieve information from Flywheel client
def retrieveFWInfo(fw: flywheel.Client, root_path=''):
    if fw is None:
        return None
    info = FwContextInfo()
    info.user.first_name = fw.get_current_user().firstname
    info.user.last_name = fw.get_current_user().lastname
    results = fw.resolve(root_path)
    info.projects = [c for c in results.children if hasattr(c, 'label') and c.label is not None]
    info.files = [c for c in results.children if hasattr(c, 'file_id')]
    return info


def imagej_viewer(request, file_path):
    if request.method == 'POST' or 'api_key' not in request.session:
        response = redirect('/')
        return response

    project_root = pathlib.Path(__file__).parent.parent.resolve()
    fw_client = flywheel.Client(request.session['api_key'])
    base_path, file_name = os.path.split(file_path)
    result = fw_client.resolve(base_path)
    project = result.path[-1]
    project.download_file(file_name, os.path.join(project_root, 'data', file_name))
    return render(request, 'home/imagej_viewer.html', {'image_file': file_name})


# Base home view
def index(request, root_path=''):
    if request.method == 'POST':
        request.session['api_key'] = request.POST['api_key']
        response = redirect('/home/projects/wandell')
        return response
    
    if not root_path and 'api_key' in request.session:
        del request.session['api_key']
    
    if 'api_key' in request.session:
        fw_client = flywheel.Client(request.session['api_key'])
        info = retrieveFWInfo(fw_client, root_path)
        info.current_path = root_path + '/'
        return render(
            request,
            'home/home_page.html',
            {'context': info})
    return render(request, 'home/index.html', {})