from django import forms
from django.core.exceptions import ValidationError
import re
from .models import Barbearia, Usuario, Assinatura

# --- Formulário Django para o modelo Barbearia ---
class BarbeariaForm(forms.ModelForm):
    class Meta:
        model = Barbearia
        fields = ['nome_barbearia', 'endereco', 'cidade', 'estado', 'cep']
        widgets = {
            'nome_barbearia': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'cep': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Apenas números (8 dígitos)',
                'maxlength': '8',
                'pattern': '[0-9]{8}',
                'inputmode': 'numeric',
                'data-mask': 'cep'
            }),
        }
        labels = {
            'nome_barbearia': 'Nome da Barbearia',
            'endereco': 'Endereço',
            'cidade': 'Cidade',
            'estado': 'Estado',
            'cep': 'CEP',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'estado' in self.fields:
            model_choices = list(Barbearia._meta.get_field('estado').choices or [])
            if not self.initial.get('estado') and ('', 'Selecione') not in model_choices:
                self.fields['estado'].widget.choices = [('', 'Selecione')] + model_choices
            else:
                self.fields['estado'].widget.choices = model_choices

    def clean_cep(self):
        cep = self.cleaned_data.get('cep')
        if not cep:
            raise ValidationError("O CEP é obrigatório.")
        
        # Remove qualquer caractere que não seja dígito
        cep_numeros = re.sub(r'\D', '', cep)
        
        # Verifica se contém apenas números
        if not cep_numeros.isdigit():
            raise ValidationError("O CEP deve conter apenas números.")
        
        # Verifica se o CEP tem exatamente 8 dígitos
        if len(cep_numeros) != 8:
            raise ValidationError("O CEP deve conter exatamente 8 dígitos.")
        
        # Verifica se não é um CEP inválido (todos os números iguais)
        if len(set(cep_numeros)) == 1:
            raise ValidationError("CEP inválido.")

        # Formata o CEP com o hífen (99999-999)
        cep_formatado = f"{cep_numeros[:5]}-{cep_numeros[5:]}"
        return cep_formatado

# --- Formulário Django para o modelo Usuário ---
class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nome_completo', 'email', 'telefone', 'aceite_termos', 'receber_notificacoes']
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Apenas números (10 ou 11 dígitos)',
                'maxlength': '11',
                'pattern': '[0-9]{10,11}',
                'inputmode': 'numeric',
                'data-mask': 'telefone'
            }),
            'aceite_termos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receber_notificacoes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nome_completo': 'Nome Completo',
            'email': 'Email',
            'telefone': 'Telefone',
            'aceite_termos': 'Aceito os Termos de Uso',
            'receber_notificacoes': 'Desejo receber notificações',
        }
        help_texts = {
            'email': 'Endereço de e-mail válido.',
            'telefone': 'Digite apenas números (DDD + número).',
            'cep': 'Digite apenas números.',
        }

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        if not telefone:
            raise ValidationError("O telefone é obrigatório.")
        
        # Remove qualquer caractere que não seja dígito
        telefone_numeros = re.sub(r'\D', '', telefone)
        
        # Verifica se contém apenas números
        if not telefone_numeros.isdigit():
            raise ValidationError("O telefone deve conter apenas números.")
        
        # Verifica se o telefone tem 10 ou 11 dígitos
        if len(telefone_numeros) not in [10, 11]:
            raise ValidationError("O telefone deve ter 10 ou 11 dígitos (incluindo o DDD).")
        
        # Verifica se o DDD é válido (não pode começar com 0 ou 1)
        if telefone_numeros[0] in ['0', '1']:
            raise ValidationError("DDD inválido. O primeiro dígito deve ser entre 2 e 9.")
        
        # Verifica se não é um número inválido (todos os dígitos iguais)
        if len(set(telefone_numeros)) == 1:
            raise ValidationError("Número de telefone inválido.")

        # Formata o telefone
        if len(telefone_numeros) == 11:
            # Formato para celular: (99)99999-9999
            telefone_formatado = f"({telefone_numeros[:2]}){telefone_numeros[2:7]}-{telefone_numeros[7:]}"
        else:
            # Formato para telefone fixo: (99)9999-9999
            telefone_formatado = f"({telefone_numeros[:2]}){telefone_numeros[2:6]}-{telefone_numeros[6:]}"
            
        return telefone_formatado

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError("O email é obrigatório.")
        
        # Validação de formato de email com regex mais rigorosa
        email_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            raise ValidationError("Por favor, insira um endereço de e-mail válido no formato nome@dominio.com.")
        
        # Verifica se o email não tem caracteres consecutivos inválidos
        if '..' in email or '--' in email or '__' in email:
            raise ValidationError("Email contém caracteres consecutivos inválidos.")
            
        # Verifica comprimento
        if len(email) > 254:
            raise ValidationError("O email é muito longo (máximo 254 caracteres).")
            
        return email.lower()  # Retorna em minúsculas para consistência

    def clean_nome_completo(self):
        nome = self.cleaned_data.get('nome_completo')
        if not nome:
            raise ValidationError("O nome completo é obrigatório.")
        
        # Remove espaços extras
        nome = ' '.join(nome.split())
        
        # Verifica se tem pelo menos nome e sobrenome
        if len(nome.split()) < 2:
            raise ValidationError("Por favor, informe seu nome completo (nome e sobrenome).")
        
        # Verifica se contém apenas letras, espaços e acentos
        if not re.match(r'^[a-zA-ZÀ-ÿ\s]+$', nome):
            raise ValidationError("O nome deve conter apenas letras e espaços.")
            
        return nome.title()  # Capitaliza corretamente

    def clean_aceite_termos(self):
        aceite_termos = self.cleaned_data.get('aceite_termos')
        if not aceite_termos:
            raise ValidationError("Você deve aceitar os termos de uso para continuar.")
        return aceite_termos

# --- Formulário Django para o modelo Assinatura ---
class AssinaturaForm(forms.ModelForm):
    """
    Formulário Django para o modelo Assinatura.
    Principalmente útil para gerenciamento em interfaces administrativas.
    """
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