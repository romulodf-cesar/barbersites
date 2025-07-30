# crm/views.py

from django.shortcuts import render
from .models import Plano # Importa o modelo Plano do CRM
# NOTA: Removido 'from crm.forms import PlanoForms' pois PlanoForms não é usado aqui.
# NOTA: Removidas as views 'checkout_plano' e 'plano_form' se existiam, pois não fazem parte
#       do fluxo de checkout Stripe que implementamos em 'payments/views.py'.

def index(request):
    """
    Renderiza a página inicial (landing page) do seu site.
    Carrega todos os Planos do CRM para exibição direta na página.
    """
    # Busca todos os objetos Plano no banco de dados e os ordena pelo valor.
    # Isso permite que os planos sejam exibidos na landing page.
    planos = Plano.objects.all().order_by('valor')
    context = {
        'planos': planos, # Passa a lista de planos para o template index.html.
        # Você pode passar outras variáveis se sua index precisar delas.
    }
    # Renderiza o template 'crm/index.html'.
    # Este template deve estar em 'sua_pasta_do_projeto/templates/crm/index.html'.
    return render(request, 'crm/index.html', context)

# Se você tem outras views no crm (que não sejam relacionadas ao Stripe Payments),
# elas deveriam ser adicionadas aqui. As views de pagamento Stripe estão em payments/views.py.






# from django.shortcuts import get_object_or_404, render

# from crm.forms import PlanoForms

# from .models import Plano


# def index(request):
#     # Pega todos os planos do banco de dados para exibir na landing page
#     planos = Plano.objects.all().order_by('valor')
#     context = {
#         'planos': planos,
#         # Você pode passar outras variáveis se sua index precisar delas
#     }
#     return render(
#         request, 'crm/index.html', context
#     )   # Renderiza a index.html


# def checkout_plano(request, plano_id):
#     plano_selecionado = get_object_or_404(Plano, id=plano_id)
#     todos_os_planos = Plano.objects.all().order_by('valor')

#     # Prepare os dados para preencher o formulário usando 'initial'
#     # As chaves aqui (ex: 'nome_do_campo_no_form') devem ser os nomes exatos
#     # dos campos definidos em sua classe PlanoForms
#     dados_iniciais_para_form = {
#         'nome_do_campo_no_form_nome': plano_selecionado.nome_plano,
#         'nome_do_campo_no_form_valor': plano_selecionado.valor,
#         # Adicione mais campos conforme o seu PlanoForms está definido,
#         # mapeando do objeto 'plano_selecionado' para os campos do formulário.
#         # Por exemplo, se seu formulário tem um campo 'descricao', e seu modelo Plano tem 'descricao':
#         # 'descricao': plano_selecionado.descricao,
#     }

#     # Agora instancie o formulário usando 'initial'
#     form = PlanoForms(initial=dados_iniciais_para_form)

#     context = {
#         'plano_selecionado': plano_selecionado,
#         'todos_os_planos': todos_os_planos,
#         'form': form,  # Passe o formulário para o contexto
#     }
#     return render(request, 'crm/checkout.html', context)


# def plano_form(request):
#     form = PlanoForms()
#     return render(request, 'crm/plano.html', {'form': form})
