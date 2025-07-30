# crm/models.py

from django.db import models
from datetime import timedelta
from django.utils import timezone # Importa timezone para trabalhar com datas e fusos horários.

class Plano(models.Model):
    """
    Define a estrutura dos planos de assinatura que sua barbearia oferece.
    Este modelo é a contraparte do "Product" e "Price" configurados no Stripe Dashboard.
    """
    # O 'id' é gerado automaticamente pelo Django como Primary Key (id).
    # Não precisamos declará-lo explicitamente.

    nome_plano = models.CharField(
        max_length=100,
        verbose_name='Nome do Plano', # Nome amigável do campo no Admin Django.
        null=False, # Não permite valores nulos no banco de dados.
        blank=False # Requer que o campo seja preenchido em formulários Django.
    )
    valor = models.DecimalField(
        max_digits=10, # Número total máximo de dígitos (ex: 99999999.99).
        decimal_places=2, # Número de casas decimais (ex: para valores em dinheiro).
        verbose_name='Valor',
        null=False,
        blank=False,
    )
    descricao = models.TextField(
        verbose_name='Descrição',
        null=True, # Permite valores nulos no banco de dados.
        blank=True # O campo pode ser deixado em branco em formulários Django.
    )

    # Campo essencial para vincular seu Plano Django a um Preço configurado no Stripe.
    # O 'price_id' do Stripe (ex: 'price_123abcDEF') é usado para identificar o plano a ser cobrado.
    stripe_price_id = models.CharField(
        max_length=100,
        unique=True, # Garante que cada Plano Django se vincule a apenas um Price ID único do Stripe.
        blank=True, # Permite que o campo fique em branco no formulário (útil se o plano ainda não foi configurado no Stripe).
        null=True, # Permite valores nulos no banco de dados (útil se o plano ainda não foi configurado no Stripe).
        verbose_name='ID do Preço no Stripe',
    )
    # Campo para definir um período de teste gratuito em dias.
    # Este valor é enviado ao Stripe para configurar o trial na sessão de checkout.
    trial_period_days = models.IntegerField(
        default=0, # O padrão é 0 dias, ou seja, sem teste gratuito.
        verbose_name='Dias de Teste Gratuito',
        help_text='Número de dias de teste gratuito para este plano de assinatura.', # Texto de ajuda no Admin Django.
    )
    # Campo para armazenar o intervalo de cobrança do plano (mensal, anual, etc.).
    # Isso é para manter a coerência com as configurações de recorrência do Stripe.
    interval = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[ # Opções predefinidas para o intervalo.
            ('day', 'Diário'),
            ('week', 'Semanal'),
            ('month', 'Mensal'),
            ('year', 'Anual'),
        ],
        verbose_name='Intervalo de Cobrança',
    )

    class Meta:
        db_table = 'crm_plano' # Define o nome da tabela no banco de dados (ex: crm_plano).
        verbose_name = 'Plano' # Nome amigável singular para o Admin Django.
        verbose_name_plural = 'Planos' # Nome amigável plural para o Admin Django.
        # Você pode adicionar outras opções Meta aqui, se necessário,
        # como ordering = ['nome_plano'] para ordenar por nome padrão no Admin.

    def __str__(self):
        """
        Retorna uma representação textual do objeto Plano, útil no Admin Django.
        """
        return self.nome_plano

    def get_display_valor_centavos(self):
        """
        Método auxiliar para converter o valor do plano para centavos (inteiro).
        O Stripe exige valores em centavos para 'unit_amount' em algumas APIs.
        """
        return int(self.valor * 100)

ESTADO_CHOICES = [
    ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
    ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'),
    ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'),
    ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'),
    ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
    ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'),
    ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins'),
]

class Barbearia(models.Model):
    """
    Representa os dados específicos de uma barbearia que contrata os serviços.
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
        max_length=2, # Ex: SP, RJ, MG (UF)
        verbose_name='Estado (UF)',
        choices=ESTADO_CHOICES, # Usa as opções definidas acima.
        null=False,
        blank=False,
    )
    cep = models.CharField(
        max_length=9, # Formato 00000-000
        verbose_name='CEP',
        null=False,
        blank=False,
    )

    class Meta:
        db_table = 'crm_barbearia'
        verbose_name = 'Barbearia'
        verbose_name_plural = 'Barbearias'

    def __str__(self):
        """
        Retorna o nome da barbearia.
        """
        return self.nome_barbearia


class Usuario(models.Model):
    """
    Representa o usuário/cliente principal que contrata os serviços da Barbearia.
    Este modelo pode ser expandido ou substituído pelo sistema de autenticação padrão do Django (User model).
    """

    nome_completo = models.CharField(
        max_length=200,
        verbose_name='Nome Completo',
        null=False,
        blank=False
    )
    email = models.EmailField(
        unique=True, # Garante que cada email seja único no banco de dados.
        verbose_name='Email',
        null=False,
        blank=False,
    )
    telefone = models.CharField(
        max_length=20, # Ex: (XX) XXXX-XXXX ou (XX) XXXXX-XXXX
        verbose_name='Telefone',
        null=False,
        blank=False,
    )
    # Campo para registrar a aceitação dos termos de uso.
    aceite_termos = models.BooleanField(
        default=False,
        verbose_name='Aceitou Termos de Uso'
    )
    # Campo para o usuário optar por receber notificações.
    receber_notificacoes = models.BooleanField(
        default=False,
        verbose_name='Deseja receber notificações'
    )
    # ID do cliente no Stripe.
    # Este campo é crucial para vincular um 'Usuario' do seu sistema a um 'Customer' no Stripe.
    # Permite que você gerencie as assinaturas e informações de pagamento do cliente via API do Stripe,
    # associando-as ao seu usuário local.
    stripe_customer_id = models.CharField(
        max_length=100,
        unique=True, # Garante que um 'Customer ID' do Stripe esteja vinculado a apenas um 'Usuario' local.
        blank=True,
        null=True,
        verbose_name='ID do Cliente no Stripe',
    )

    class Meta:
        db_table = 'crm_usuario'
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        """
        Retorna o nome completo do usuário.
        """
        return self.nome_completo


class Assinatura(models.Model):
    """
    Representa a relação de assinatura entre um Usuário, um Plano e uma Barbearia.
    Este modelo armazena o status do pagamento e o tipo de acesso do usuário.
    É o modelo principal para gerenciar o ciclo de vida da assinatura no sistema.
    """

    # Opções para o status da assinatura, alinhadas com os status que o Stripe pode retornar.
    STATUS_ASSINATURA_CHOICES = [
        ('trialing', 'Em Período de Teste'), # Assinatura está em período de teste gratuito.
        ('active', 'Ativa'), # Assinatura está ativa e sendo cobrada.
        ('past_due', 'Vencida'), # Pagamento falhou, mas Stripe ainda tenta cobrar.
        ('canceled', 'Cancelada'), # Assinatura foi cancelada.
        ('unpaid', 'Não Paga'), # Stripe parou de tentar cobrar a fatura.
    ]

    # Opções para o status do usuário (tipo de acesso), conforme a lógica de negócio do sistema.
    STATUS_USUARIO_CHOICES = [
        ('padrao', 'Usuário Padrão'), # Nível de acesso básico.
        ('premium', 'Usuário Premium'), # Nível de acesso com funcionalidades premium.
        ('admin', 'Administrador'), # Nível de acesso administrativo.
    ]

    # Chave estrangeira para o 'Usuario' que fez esta assinatura.
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE, # Se o 'Usuario' for deletado, suas 'Assinaturas' também serão.
        related_name='assinaturas', # Permite acessar assinaturas de um usuário via usuario.assinaturas.all().
        verbose_name='Usuário',
    )

    # Chave estrangeira para o 'Plano' que foi contratado nesta assinatura.
    plano = models.ForeignKey(
        Plano,
        on_delete=models.PROTECT, # Não permite deletar um 'Plano' se houver 'Assinaturas' vinculadas a ele.
        related_name='assinaturas', # Permite acessar assinaturas de um plano via plano.assinaturas.all().
        verbose_name='Plano Contratado',
    )

    # Chave estrangeira para a 'Barbearia' associada a esta assinatura.
    barbearia = models.ForeignKey(
        Barbearia,
        on_delete=models.CASCADE, # Se a 'Barbearia' for deletada, suas 'Assinaturas' também serão.
        related_name='assinaturas',
        verbose_name='Barbearia Associada',
    )

    # Campo para armazenar o status principal da assinatura, alinhado com o Stripe.
    status_assinatura = models.CharField(
        max_length=20,
        choices=STATUS_ASSINATURA_CHOICES, # Usa as opções predefinidas acima.
        default='trialing', # Valor padrão quando uma nova assinatura é criada.
        verbose_name='Status da Assinatura',
    )

    # Campo para definir o status de acesso do usuário no sistema.
    status_usuario = models.CharField(
        max_length=20,
        choices=STATUS_USUARIO_CHOICES,
        default='padrao',
        verbose_name='Status do Usuário',
    )

    # ID da assinatura no Stripe.
    # Este é o ID principal que conecta esta 'Assinatura' local com a 'Subscription' no Stripe.
    # É fundamental para fazer chamadas à API do Stripe relacionadas a esta assinatura.
    stripe_subscription_id = models.CharField(
        max_length=100,
        unique=True, # Garante que cada 'Subscription ID' do Stripe tenha apenas um registro local.
        blank=True,
        null=True,
        verbose_name='ID da Assinatura no Stripe',
    )

    # Campo para armazenar o ID da transação específica do gateway de pagamento.
    # Útil para rastrear pagamentos individuais (ex: Payment Intent ID de uma fatura).
    id_transacao_pagamento = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True, # A ID da transação deve ser única.
        verbose_name='ID da Transação de Pagamento',
    )

    # Data de Início do Período Atual da Assinatura (baseado em current_period_start do Stripe).
    # Marca o início do ciclo de faturamento ou período de teste atual.
    data_inicio = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Início do Período'
    )
    # Data de Término do Período Atual da Assinatura (baseado em current_period_end do Stripe).
    # Marca o fim do ciclo de faturamento atual e o início do próximo.
    data_expiracao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Término do Período'
    )
    # Data de término do período de teste gratuito (baseado em trial_end do Stripe).
    # Este campo só é preenchido para assinaturas que estão em período de teste.
    trial_end = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fim do Período de Teste'
    )

    class Meta:
        db_table = 'crm_assinatura'
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'
        # unique_together = ('usuario', 'plano', 'barbearia',)
        # Esta linha (comentada) garantiria que um usuário só tenha uma assinatura
        # para um plano específico em uma determinada barbearia ao mesmo tempo.
        # Descomente se essa lógica de negócio for necessária para você.

    def __str__(self):
        """
        Retorna uma representação textual da assinatura.
        """
        return f'Assinatura de {self.usuario.nome_completo} para {self.plano.nome_plano} ({self.status_assinatura})'

    # --- Métodos Auxiliares para Atualizar o Status da Assinatura ---
    # Estes métodos são chamados principalmente pelo Webhook do Stripe
    # para manter o modelo 'Assinatura' sincronizado com o Stripe.

    def set_status_and_dates(
        self,
        status,
        current_period_start=None, # Parâmetro para a data de início do período atual
        current_period_end=None, # Parâmetro para a data de término do período atual
        trial_end=None, # Parâmetro para a data de término do trial
    ):
        """
        Define o status da assinatura e atualiza suas datas de início, expiração e término do trial.
        Recebe objetos datetime (preferencialmente timezone-aware).
        """
        self.status_assinatura = status
        self.data_inicio = current_period_start
        self.data_expiracao = current_period_end
        self.trial_end = trial_end
        self.save() # Salva as alterações no banco de dados.

    def registrar_pagamento_sucesso(self, payment_intent_id=None):
        """
        Marca a assinatura como 'active' (ativa) após um sucesso de pagamento.
        """
        self.status_assinatura = 'active'
        self.id_transacao_pagamento = payment_intent_id  # Armazena o ID da transação.
        self.save() # Salva as alterações.

    def registrar_cancelamento(self):
        """
        Marca a assinatura como 'canceled' (cancelada) e invoca a lógica de revogação de acesso.
        """
        self.status_assinatura = 'canceled'
        # A 'data_expiracao' não é necessariamente marcada como "agora",
        # pois o acesso pode continuar até o final do período pago.
        # self.data_expiracao = timezone.now() # Opcional: descomente se quiser marcar a expiração no cancelamento.
        self.save() # Salva as alterações.
        self.revogar_acesso() # Chama a função para revogar acesso.

    def registrar_falha_pagamento(self):
        """
        Marca a assinatura como 'past_due' (vencida) ou 'unpaid' (não paga)
        após uma falha na tentativa de cobrança.
        """
        self.status_assinatura = 'past_due' # Alinha com um status comum do Stripe para falha.
        self.save() # Salva as alterações.
        # Aqui, você pode implementar lógica adicional para limitar ou suspender o acesso temporariamente.

    def revogar_acesso(self):
        """
        Lógica de negócio para desativar o acesso do usuário no seu sistema
        quando a assinatura não está mais ativa ou foi cancelada.
        """
        # Exemplo: Se o seu modelo 'Usuario' tivesse um campo 'is_premium', você o definiria como False.
        # self.usuario.is_premium = False
        # self.usuario.save()
        print(
            f'Acesso de {self.usuario.nome_completo} revogado para o plano {self.plano.nome_plano}.'
        )

    def conceder_acesso(self):
        """
        Lógica de negócio para ativar o acesso do usuário no seu sistema
        quando a assinatura está 'trialing' ou 'active'.
        """
        # Exemplo: Se o seu modelo 'Usuario' tivesse um campo 'is_premium', você o definiria como True.
        # self.usuario.is_premium = True
        # self.usuario.save()
        print(
            f'Acesso de {self.usuario.nome_completo} concedido para o plano {self.plano.nome_plano}.'
        )