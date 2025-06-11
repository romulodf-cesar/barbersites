from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return HttpResponse('<h3> BarberSites</h3> <p> O App do Barbeiro Empreendedor </p>')

