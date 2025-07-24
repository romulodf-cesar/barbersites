from django.shortcuts import get_object_or_404, render,redirect
from crm.models import Plano
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


def plano_form(request):
    form = PlanoForms()
    return render(request, 'crm/plano.html', {'form': form})
# função para criar um novo plano.
def criar_plano(request): # Renomeei a função para deixar o propósito mais claro
    if request.method == 'POST':
        form = PlanoForms(request.POST) # Instancia o formulário com os dados enviados
        if form.is_valid(): # Verifica se o formulário é válido
            nome_plano = form.cleaned_data['nome_plano']
            valor = form.cleaned_data['valor']
            descricao = form.cleaned_data['descricao']

            # Crie uma nova instância do modelo Plano com os dados
            novo_plano = Plano(
                nome_plano=nome_plano,
                valor=valor,
                descricao=descricao
            )
            novo_plano.save() # Salva a nova instância no banco de dados

            return redirect('home') # Redireciona para a página inicial após salvar com sucesso
    else: # Se for um GET request, exibe um formulário vazio
        form = PlanoForms()
    
    return render(request, 'crm/plano.html', {'form': form})



