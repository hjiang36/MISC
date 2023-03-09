from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.urls import reverse

from .models import FwContextInfo

import flywheel

# Retrieve information from Flywheel client
def retrieveFWInfo(fw: flywheel.Client, root_path=''):
    if fw is None:
        return None
    info = FwContextInfo()
    info.user.first_name = fw.get_current_user().firstname
    info.user.last_name = fw.get_current_user().lastname
    info.projects = fw.resolve(root_path).children
    return info

# Base home view
def index(request, root_path=''):
    if request.method == 'POST':
        request.session['api_key'] = request.POST['api_key']
        response = redirect('/')
        return response
    
    if not root_path:
        root_path = 'wandell'
    
    if 'api_key' in request.session:
        print("---------------------------------------root_paht: " + root_path)
        fw_client = flywheel.Client(request.session['api_key'])
        info = retrieveFWInfo(fw_client, root_path)
        info.current_path = root_path + '/'
        return render(
            request,
            'home/home_page.html',
            {'context': info})
    return render(request, 'home/index.html', {})