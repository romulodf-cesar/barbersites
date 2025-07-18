from django.shortcuts import get_object_or_404, render
from .models import Plano
from crm.forms import PlanoForms

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
    plano_selecionado = get_object_or_404(Plano, id=plano_id)
    todos_os_planos = Plano.objects.all().order_by('valor')

    # Prepare os dados para preencher o formulário usando 'initial'
    # As chaves aqui (ex: 'nome_do_campo_no_form') devem ser os nomes exatos
    # dos campos definidos em sua classe PlanoForms
    dados_iniciais_para_form = {
        'nome_do_campo_no_form_nome': plano_selecionado.nome_plano,
        'nome_do_campo_no_form_valor': plano_selecionado.valor,
        # Adicione mais campos conforme o seu PlanoForms está definido,
        # mapeando do objeto 'plano_selecionado' para os campos do formulário.
        # Por exemplo, se seu formulário tem um campo 'descricao', e seu modelo Plano tem 'descricao':
        # 'descricao': plano_selecionado.descricao,
    }

    # Agora instancie o formulário usando 'initial'
    form = PlanoForms(initial=dados_iniciais_para_form)

    context = {
        'plano_selecionado': plano_selecionado,
        'todos_os_planos': todos_os_planos,
        'form': form, # Passe o formulário para o contexto
    }
    return render(request, 'crm/checkout.html', context)