from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.urls import reverse

import flywheel

# Retrieve information from Flywheel client
def retrieveFWInfo(fw: flywheel.Client, root_path=''):
    if fw is None:
        return {}
    info = dict()
    info["first_name"] = fw.get_current_user().firstname
    info["last_name"] = fw.get_current_user().lastname
    info["projects"] = fw.resolve(root_path).children


# Project list index page
def home_page(request, fw_client: flywheel.Client=None):
    if request.method == 'POST':
        # raise 404 not found error
        raise Http404('Target request not avaiable')
    if fw_client is None:
        redirect(index)
    return render(request, 'home/home_page.html', retrieveFWInfo(fw_client, 'wandell'))

# Base home view
def index(request):
    if request.method == 'POST':
        api_key = request.POST["APIKey"]
        redirect(reverse(home_page, kwargs={'fw_client': flywheel.Client(api_key)}))
    return render(request, 'home/index.html', {})