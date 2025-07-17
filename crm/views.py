from django.shortcuts import get_object_or_404, render
from .models import Plano

def index(request):
    """
    Renderiza a página inicial (Home) exibindo todos os planos disponíveis.
    Os planos são ordenados pelo valor.
    """
    planos = Plano.objects.all().order_by('valor')
    context = {
        'planos': planos,
    }
    return render(request, 'crm/index.html', context)

def checkout_plano(request, plano_id):
    """
    Renderiza a página de checkout para um plano específico.
    
    Recebe o 'plano_id' da URL, busca o plano correspondente e também 
    recupera todos os planos para preencher o dropdown de seleção.
    """
    # Busca o plano que foi selecionado pelo usuário na página anterior
    plano_selecionado = get_object_or_404(Plano, id=plano_id)

    # Busca todos os planos para popular o dropdown de "Mudar Plano" na página de checkout
    todos_os_planos = Plano.objects.all().order_by('valor') 

    context = {
        'plano_selecionado': plano_selecionado, # O objeto do plano que será destacado no checkout
        'todos_os_planos': todos_os_planos,     # A lista completa de planos para o <select>
    }
    # Atenção ao caminho do template: 'crm/checkout.html' é o mais comum para apps.
    return render(request, 'crm/checkout.html', context)