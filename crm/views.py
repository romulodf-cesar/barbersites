from django.shortcuts import render

def index(request):
    return render(request, 'crm/index.html')

def checkout(request):
    return render(request, 'crm/checkout.html')
