# crm/admin.py

# Importa o módulo admin do Django.
from django.contrib import admin
# Importa todos os modelos necessários do seu próprio aplicativo 'crm'.
# Também importa ESTADO_CHOICES diretamente do models para usar nas choices do admin.
from .models import Plano, Barbearia, Usuario, Assinatura, ESTADO_CHOICES 


# --- Classe Admin para o modelo Plano ---
# @admin.register(Plano) é um decorador que registra o modelo 'Plano' com esta classe de administração.
@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    """
    Define a interface de administração para o modelo 'Plano'.
    Configura como os planos serão exibidos e gerenciados no Django Admin.
    """
    # list_display: Define quais campos do modelo serão exibidos na lista de objetos no Admin.
    list_display = (
        
        'nome_plano',
        'valor',
        'stripe_price_id',      # Mostra o ID do preço do Stripe associado.
        'trial_period_days',    # Mostra os dias de teste gratuito.
        'interval',             # Mostra o intervalo de cobrança (Mensal, Anual, etc.).
        'descricao_curta',      # Adiciona o método personalizado 'descricao_curta' à exibição da lista.
    )
    # list_filter: Permite filtrar a lista de objetos por esses campos na barra lateral direita do Admin.
    list_filter = ('interval', 'nome_plano',)
    # search_fields: Define os campos que serão pesquisados quando o usuário usar a barra de pesquisa do Admin.
    search_fields = ('nome_plano', 'descricao', 'stripe_price_id')
    # fields: (Opcional) Define a ordem e quais campos aparecem no formulário de edição/criação do objeto.
    # Se não definido, o Django mostra todos os fields do model. Pode ser útil para organizar.
    # fields = ('nome_plano', 'valor', 'descricao', 'stripe_price_id', 'trial_period_days', 'interval')

    # Método personalizado para exibir uma versão curta da descrição na list_display.
    # Útil para descrições longas, evitando que a tabela fique muito grande.
    def descricao_curta(self, obj):
        return (
            (obj.descricao[:50] + '...') # Limita a descrição a 50 caracteres e adiciona '...'
            if obj.descricao and len(obj.descricao) > 50 # Verifica se a descrição existe e é maior que 50.
            else obj.descricao # Se for curta ou vazia, exibe-a inteira.
        )
    descricao_curta.short_description = 'Descrição' # Define o cabeçalho da coluna para este método na list_display.


# --- Classe Admin para o modelo Barbearia ---
@admin.register(Barbearia)
class BarbeariaAdmin(admin.ModelAdmin):
    """
    Define a interface de administração para o modelo 'Barbearia'.
    """
    list_display = (
        'id',
        'nome_barbearia',
        'endereco',
        'cidade',
        'estado',
        'cep',
    )
    list_filter = ('estado', 'cidade',)
    search_fields = ('nome_barbearia', 'endereco', 'cidade', 'cep')

    # NOVO/CORRIGIDO: Método para personalizar o campo 'estado' no formulário do Admin.
    # Isso é necessário para garantir que as opções do Select serão carregadas corretamente no Admin.
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        # Verifica se o campo do banco de dados que está sendo renderizado é o campo 'estado'.
        if db_field.name == "estado": 
            # Define as escolhas para este campo usando a lista ESTADO_CHOICES importada do modelo.
            kwargs['choices'] = ESTADO_CHOICES
            # Você pode adicionar um 'initial' ou um 'empty_label' aqui se quiser personalizar o Select.
            # Ex: kwargs['empty_label'] = "Selecione um Estado"
        # Chama o método original do pai (ModelAdmin) para os outros campos ou para finalizar este.
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    # REMOVIDO: O método 'descricao_curta' foi removido desta classe.
    # Motivo: O modelo 'Barbearia' não possui um campo chamado 'descricao'.
    # Isso causaria um AttributeError se tentasse acessá-lo.


# --- Classe Admin para o modelo Usuário ---
@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    """
    Define a interface de administração para o modelo 'Usuário'.
    """
    list_display = (
        'id',
        'nome_completo',
        'email',
        'telefone',
        'aceite_termos',
        'receber_notificacoes',
        'stripe_customer_id', # Adicionado para visibilidade no Admin.
    )
    list_filter = ('aceite_termos', 'receber_notificacoes',)
    search_fields = ('nome_completo', 'email', 'telefone', 'stripe_customer_id')
    # readonly_fields: Campos que não podem ser editados manualmente no Admin,
    # pois seus valores são gerenciados automaticamente pelo sistema (especialmente por webhooks do Stripe).
    readonly_fields = ('stripe_customer_id',) 

    # REMOVIDO: O método 'descricao_curta' foi removido desta classe.
    # Motivo: O modelo 'Usuario' não possui um campo chamado 'descricao'.


# --- Classe Admin para o modelo Assinatura ---
@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    """
    Define a interface de administração para o modelo 'Assinatura'.
    Configura como as assinaturas serão exibidas e gerenciadas no Django Admin.
    """
    list_display = (
        'id',
        'usuario',
        'plano',
        'barbearia',
        'status_assinatura',      # Status atual da assinatura (ex: trialing, active).
        'status_usuario',         # Nível de acesso do usuário no seu sistema.
        'data_inicio',            # Data de início do período atual da assinatura.
        'data_expiracao',         # Data de fim do período atual da assinatura.
        'trial_end',              # Data de fim do período de teste (se houver).
        'stripe_subscription_id', # ID da assinatura no Stripe.
        'id_transacao_pagamento', # ID da última transação de pagamento.
    )
    # Filtros que aparecem na barra lateral direita do Admin.
    list_filter = ('status_assinatura', 'status_usuario', 'plano', 'barbearia',)
    # Campos para busca na barra de pesquisa do Admin.
    search_fields = (
        'usuario__nome_completo',      # Permite buscar pelo nome completo do usuário relacionado.
        'plano__nome_plano',           # Permite buscar pelo nome do plano relacionado.
        'barbearia__nome_barbearia',   # Permite buscar pelo nome da barbearia relacionada.
        'stripe_subscription_id',      # Busca por ID da assinatura no Stripe.
        'id_transacao_pagamento',      # Busca por ID da transação de pagamento.
    )
    # raw_id_fields: Melhora a performance em formulários de edição para campos ForeignKey/OneToOne,
    # substituindo o dropdown por um campo de texto que permite buscar pelo ID.
    raw_id_fields = ('usuario', 'plano', 'barbearia',)
    # readonly_fields: Campos que não podem ser editados manualmente no Admin,
    # pois são gerenciados automaticamente pelo sistema (principalmente por webhooks do Stripe).
    readonly_fields = (
        'stripe_subscription_id',
        'id_transacao_pagamento',
        'data_inicio',
        'data_expiracao',
        'trial_end',
    )
    # fields: (Opcional) Define a ordem e quais campos aparecem no formulário de edição/criação.
    # Se não definido, o Django mostra todos os fields do model.
    # fields = (
    #     'usuario', 'plano', 'barbearia', 'status_assinatura', 'status_usuario',
    #     'stripe_subscription_id', 'id_transacao_pagamento',
    #     'data_inicio', 'data_expiracao', 'trial_end'
    # )

    # REMOVIDO: O método 'descricao_curta' foi removido desta classe.
    # Motivo: O modelo 'Assinatura' não possui um campo chamado 'descricao'.