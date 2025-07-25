# crm/models.py

from datetime import timedelta

from django.db import models
from django.utils import timezone  # Adicionar para cálculos de data/hora


class Plano(models.Model):
    # O 'id' é gerado automaticamente pelo Django como Primary Key (id).
    # Não precisamos declará-lo explicitamente.

    nome_plano = models.CharField(
        max_length=100, verbose_name='Nome do Plano', null=False, blank=False
    )
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor',
        null=False,
        blank=False,
    )
    descricao = models.TextField(
        verbose_name='Descrição', null=True, blank=True
    )

    # NOVO CAMPO: ID do preço/plano criado no Stripe Dashboard
    # Este campo é essencial para vincular seu Plano Django a um Preço configurado no Stripe.
    # Quando você cria uma sessão de checkout, você informa ao Stripe qual é o "Price ID".
    stripe_price_id = models.CharField(
        max_length=100,
        unique=True,  # Garante que não haja dois Planos Django com o mesmo Price ID do Stripe
        blank=True,
        null=True,
        verbose_name='ID do Preço no Stripe',
    )
    # NOVO CAMPO: Período de teste gratuito em dias
    # Usado para configurar o trial na sessão de checkout do Stripe.
    trial_period_days = models.IntegerField(
        default=0,
        verbose_name='Dias de Teste Gratuito',
        help_text='Número de dias de teste gratuito para este plano de assinatura.',
    )
    # Adicionando um campo para o intervalo do plano, para coerência com Stripe
    # Este campo é importante para a lógica de cálculo de expiração da assinatura.
    interval = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ('day', 'Diário'),
            ('week', 'Semanal'),
            ('month', 'Mensal'),
            ('year', 'Anual'),
        ],
        verbose_name='Intervalo de Cobrança',
    )

    class Meta:
        db_table = 'crm_plano'   # Nome da tabela no banco de dados
        verbose_name = 'Plano'
        verbose_name_plural = 'Planos'
        # Você pode adicionar outras opções Meta aqui, se necessário,
        # como ordering = ['nome_plano'] para ordenar por nome padrão.

    def __str__(self):
        # Representação textual de um objeto Plano
        return self.nome_plano

    def get_display_valor_centavos(self):
        # Método auxiliar para converter o valor do plano para centavos,
        # que é o formato exigido pela API do Stripe para `unit_amount` (embora para assinaturas
        # via `stripe_price_id` o valor já esteja no plano do Stripe).
        # Mantido por coerência, caso precise de um pagamento único avulso.
        return int(self.valor * 100)


class Barbearia(models.Model):
    """
    Representa os dados específicos da barbearia.
    """

    nome_barbearia = models.CharField(
        max_length=200,
        verbose_name='Nome da Barbearia',
        null=False,
        blank=False,
    )
    endereco = models.CharField(
        max_length=255,
        verbose_name='Endereço Completo',
        null=False,
        blank=False,
    )
    cidade = models.CharField(
        max_length=100, verbose_name='Cidade', null=False, blank=False
    )
    estado = models.CharField(
        max_length=2,  # Ex: SP, RJ, MG
        verbose_name='Estado (UF)',
        null=False,
        blank=False,
    )
    cep = models.CharField(
        max_length=9,  # Formato 00000-000
        verbose_name='CEP',
        null=False,
        blank=False,
    )

    class Meta:
        db_table = 'crm_barbearia'
        verbose_name = 'Barbearia'
        verbose_name_plural = 'Barbearias'

    def __str__(self):
        return self.nome_barbearia


class Usuario(models.Model):
    """
    Representa o usuário/cliente principal que contrata os serviços.
    """

    # Se você for usar o sistema de autenticação padrão do Django,
    # pode considerar estender o User model do Django.
    # Por enquanto, vamos criar campos básicos aqui.
    nome_completo = models.CharField(
        max_length=200, verbose_name='Nome Completo', null=False, blank=False
    )
    email = models.EmailField(
        unique=True,  # Garante que cada email seja único
        verbose_name='Email',
        null=False,
        blank=False,
    )
    telefone = models.CharField(
        max_length=20,  # Ex: (XX) XXXX-XXXX ou (XX) XXXXX-XXXX
        verbose_name='Telefone',
        null=False,
        blank=False,
    )
    # Campo para aceitação de termos e notificações
    aceite_termos = models.BooleanField(
        default=False, verbose_name='Aceitou Termos de Uso'
    )
    receber_notificacoes = models.BooleanField(
        default=False, verbose_name='Deseja receber notificações'
    )
    # NOVO CAMPO: ID do cliente no Stripe
    # Este campo é fundamental para vincular um usuário do seu sistema a um cliente no Stripe.
    # Permite gerenciar as assinaturas e informações de pagamento do cliente via API do Stripe.
    stripe_customer_id = models.CharField(
        max_length=100,
        unique=True,  # Um cliente Stripe deve estar vinculado a apenas um Usuário local
        blank=True,
        null=True,
        verbose_name='ID do Cliente no Stripe',
    )

    class Meta:
        db_table = 'crm_usuario'
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        return self.nome_completo


class Assinatura(models.Model):
    """
    Representa a relação entre um Usuário, um Plano e uma Barbearia,
    contendo o status do pagamento e o tipo de acesso.
    """

    # Opções para o status da assinatura/pagamento
    # É bom alinhar esses status com os status possíveis do Stripe para facilitar a sincronização.
    STATUS_ASSINATURA_CHOICES = [  # Renomeado para maior clareza
        ('trialing', 'Em Período de Teste'),
        ('active', 'Ativa'),
        ('past_due', 'Vencida'),  # Pagamento falhou, mas Stripe ainda tenta
        ('canceled', 'Cancelada'),
        ('unpaid', 'Não Paga'),  # Stripe parou de tentar cobrar
        # 'pendente' ou 'pago' podem ser usados para status intermediários ou de pagamento único,
        # mas para assinaturas, os status do Stripe são mais robustos.
    ]

    # Opções para o status do usuário (tipo de acesso) - pode ser ajustado conforme a lógica do seu negócio
    STATUS_USUARIO_CHOICES = [
        ('padrao', 'Usuário Padrão'),
        ('premium', 'Usuário Premium'),
        ('admin', 'Administrador'),
    ]

    # Chave estrangeira para o Usuário que fez a assinatura
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,  # Se o usuário for deletado, a assinatura também é
        related_name='assinaturas',
        verbose_name='Usuário',
    )

    # Chave estrangeira para o Plano contratado
    plano = models.ForeignKey(
        Plano,
        on_delete=models.PROTECT,  # Não permite deletar um plano se houver assinaturas ativas
        related_name='assinaturas',
        verbose_name='Plano Contratado',
    )

    # Chave estrangeira para a Barbearia associada a esta assinatura
    barbearia = models.ForeignKey(
        Barbearia,
        on_delete=models.CASCADE,  # Se a barbearia for deletada, as assinaturas dela também
        related_name='assinaturas',
        verbose_name='Barbearia Associada',
    )

    # O status principal da assinatura, alinhado com o Stripe
    status_assinatura = models.CharField(  # Renomeado de status_pagamento para status_assinatura
        max_length=20,
        choices=STATUS_ASSINATURA_CHOICES,
        default='trialing',  # Um novo registro de assinatura começa tipicamente como 'trialing' ou 'active'
        verbose_name='Status da Assinatura',
    )

    status_usuario = models.CharField(
        max_length=20,
        choices=STATUS_USUARIO_CHOICES,
        default='padrao',
        verbose_name='Status do Usuário',
    )

    # NOVO CAMPO: ID da assinatura no Stripe
    # Este é o ID principal que conecta sua Assinatura local com a Assinatura no Stripe.
    stripe_subscription_id = models.CharField(
        max_length=100,
        unique=True,  # Garante que cada assinatura Stripe tenha apenas um registro local
        blank=True,
        null=True,
        verbose_name='ID da Assinatura no Stripe',
    )

    # Campo para armazenar o ID da transação do gateway de pagamento (Payment Intent ID)
    # É útil para rastrear a transação específica que criou/renovou a assinatura.
    id_transacao_pagamento = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,  # A ID da transação deve ser única
        verbose_name='ID da Transação de Pagamento',
    )

    # Data de Início do Período Atual da Assinatura (Stripe current_period_start)
    # Onde o período de cobrança ou trial começou.
    data_inicio = models.DateTimeField(
        null=True, blank=True, verbose_name='Data de Início do Período'
    )
    # Data de Término do Período Atual da Assinatura (Stripe current_period_end)
    # Quando o próximo período de cobrança inicia.
    data_expiracao = models.DateTimeField(
        null=True, blank=True, verbose_name='Data de Término do Período'
    )
    # Data de término do período de teste (Stripe trial_end)
    # Este campo é exclusivo para assinaturas em trial.
    trial_end = models.DateTimeField(
        null=True, blank=True, verbose_name='Fim do Período de Teste'
    )

    class Meta:
        db_table = 'crm_assinatura'
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'
        # O unique_together foi mantido comentado por ser uma decisão de negócio complexa.
        # unique_together = ('usuario', 'plano', 'barbearia',)

    def __str__(self):
        return f'Assinatura de {self.usuario.nome_completo} para {self.plano.nome_plano} ({self.status_assinatura})'

    # --- Métodos Auxiliares para Atualizar o Status da Assinatura ---
    # Estes métodos são chamados principalmente pelo Webhook do Stripe.

    def set_status_and_dates(
        self,
        status,
        current_period_start=None,
        current_period_end=None,
        trial_end=None,
    ):
        """
        Define o status da assinatura e suas datas de início/expiração/trial.
        Usa datetime objects (preferencialmente timezone-aware).
        """
        self.status_assinatura = status
        self.data_inicio = current_period_start
        self.data_expiracao = current_period_end
        self.trial_end = trial_end
        self.save()

    def registrar_pagamento_sucesso(self, payment_intent_id=None):
        """
        Marca a assinatura como ativa/paga após um sucesso de pagamento.
        """
        self.status_assinatura = 'active'
        self.id_transacao_pagamento = payment_intent_id   # Pode ser None
        self.save()

    def registrar_cancelamento(self):
        """
        Marca a assinatura como cancelada e revoga o acesso.
        """
        self.status_assinatura = 'canceled'
        # Não necessariamente marca a data de expiração como "agora",
        # pois o acesso pode continuar até o final do período pago.
        # self.data_expiracao = timezone.now() # Opcional, dependendo da sua regra de negócio
        self.save()
        self.revogar_acesso()

    def registrar_falha_pagamento(self):
        """
        Marca a assinatura como vencida ou não paga.
        """
        # Stripe pode setar como 'past_due' ou 'unpaid'
        self.status_assinatura = 'past_due'   # Ou 'unpaid'
        self.save()
        # Aqui, você pode implementar lógica para limitar ou suspender o acesso temporariamente.

    def revogar_acesso(self):
        """
        Lógica para desativar o acesso do usuário no seu sistema quando a assinatura não está ativa.
        Ex: desmarcar funcionalidades premium, enviar e-mail de aviso.
        """
        # Exemplo: Se Usuario tivesse um campo 'is_premium'
        # self.usuario.is_premium = False
        # self.usuario.save()
        print(
            f'Acesso de {self.usuario.nome_completo} revogado para o plano {self.plano.nome_plano}.'
        )

    def conceder_acesso(self):
        """
        Lógica para ativar o acesso do usuário no seu sistema quando a assinatura está ativa.
        Ex: marcar funcionalidades premium, etc.
        """
        # Exemplo:
        # self.usuario.is_premium = True
        # self.usuario.save()
        print(
            f'Acesso de {self.usuario.nome_completo} concedido para o plano {self.plano.nome_plano}.'
        )
