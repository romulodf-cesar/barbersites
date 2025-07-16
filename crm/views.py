from django.shortcuts import render
from .models import Plano

def index(request):
    return render(request, 'crm/index.html')

def checkout(request):
    return render(request, 'crm/checkout.html')

def checkout_view(request):
    # Buscar todos os planos do banco de dados, ordenados pelo valor, por exemplo
    planos = Plano.objects.all().order_by('valor')

    context = {
        'planos': planos, # Passe a lista de planos para o template
        # ... outros dados que você possa precisar no template (ex: formulários)
    }
    return render(request, 'crm/checkout.html', context)
