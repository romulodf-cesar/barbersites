"""
Em que situação podemos usar uma nova camada forms no Django.

Resposta:

Em várias situações, principalmente quando precisar de validação de dados,
limpeza de dados e renderização de formulários.

Veja as principais situações:

- Processamento de Entrada do Usuário (aplicação dos métodos GET e POST);

- Validação e Limpeza de Dados (*garantir a integridade dos dados antes de salvá-los no banco de dados ou processá-los de outra forma);

- Criação de Formulários para Modelos (* método: ModelForms)

- Reaproveitamento de Lógica (reaproveitamento do código);

- Integração com Ferramentas de Terceiros (* Muitos pacotes e bibliotecas de terceiros para Django - como Django REST Framework, Django Crispy Forms, etc.) se integram perfeitamente com o sistema de forms.)

- Formulários sem um Modelo Associado: Nem todo formulário precisa estar diretamente ligado a um modelo de banco de dados.
Dentro podemos usar a nossa orientação a objetos para criar formulários que representem os modelos do Django.




from django import forms
from .models import Barbearia, Usuario, Assinatura

class BarbeariaForm(forms.ModelForm):
    class Meta:
        model = Barbearia
        fields = ['nome_barbearia', 'endereco', 'cep']
        widgets = {
            'nome_barbearia': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000'}),
        }
        labels = {
            'nome_barbearia': 'Nome da Barbearia',
            'endereco': 'Endereço',
            'cep': 'CEP',
        }
class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nome_completo', 'email', 'telefone', 'aceite_termos', 'receber_notificacoes']
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(XX) XXXX-XXXX'}),
            'aceite_termos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receber_notificacoes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nome_completo': 'Nome Completo',
            'email': 'Email',
            'telefone': 'Telefone',
            'aceite_termos': 'Aceitou os Termos de Uso',
            'receber_notificacoes': 'Deseja receber notificações?',
        }
class AssinaturaForm(forms.ModelForm):
    class Meta:
        model = Assinatura
        fields = ['usuario', 'barbearia', 'plano']
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-control'}),
            'barbearia': forms.Select(attrs={'class': 'form-control'}),
            'plano': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'usuario': 'Usuário',
            'barbearia': 'Barbearia',
            'plano': 'Plano',
        }
"""

# Orientação a Objetos

from django import forms

from .models import Plano


# Herança de classes
class PlanoForms(forms.Form):
    nome_plano = forms.CharField(
        max_length=100,  # quantidade de caracteres
        required=True,  # campo obrigatório
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Nome do Plano',  # rótulo do campo
    )
    valor = forms.DecimalField(
        max_digits=10,  # número máximo de dígitos
        decimal_places=2,  # número de casas decimais
        required=True,  # campo obrigatório
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Valor do Plano',  # rótulo do campo
    )
    descricao = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,  # campo opcional
        label='Descrição do Plano',  # rótulo do campo
    )
