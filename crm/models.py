from django.db import models
from datetime import timedelta
from django.utils import timezone # Importa timezone para trabalhar com datas e fusos horários.
from django.contrib.auth.models import User, Group # Importa o modelo User e Group do sistema de autenticação do Django.
from .utils import generate_random_password, senha_chumbada # Importa a função de gerar senha aleatória que criamos em crm/utils.py.
from django.core.mail import send_mail # Importa send_mail para enviar e-mails.
from django.conf import settings # Importa settings para acessar DEFAULT_FROM_EMAIL.
from django.core.exceptions import ObjectDoesNotExist # Importa ObjectDoesNotExist para tratar caso o OneToOneField 'user' não exista.
from django.template.loader import render_to_string # NOVO: Importa para renderizar templates de email.


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

    # NOVO CAMPO: Vincula este Usuario a um User do sistema de autenticação do Django.
    # Um OneToOneField significa que cada Usuario terá um e apenas um User correspondente,
    # e vice-versa.
    user = models.OneToOneField(
        User, # Referencia o modelo User padrão do Django.
        on_delete=models.CASCADE, # Se o User for deletado, este Usuario também será.
        null=True, blank=True,    # Permite que um Usuario exista sem um User inicialmente, ou vice-versa.
                                  # Útil se o User for criado em um fluxo separado.
                                  # Em nosso caso, vamos criar o User junto com a concessão de acesso.
        related_name='crm_profile', # Nome para acessar este perfil CRM a partir do User (User.crm_profile).
        verbose_name="Usuário do Sistema"
    )

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
    # Indica se a assinatura foi cancelada para o final do período de cobrança.
    # Se True, o acesso continua até data_expiracao, depois é revogado.
    # Se False, o acesso é revogado imediatamente (se o status permitir).
    cancel_at_period_end = models.BooleanField(
        default=False, 
        verbose_name="Cancelar no final do período",
        help_text="Se True, o acesso será revogado apenas ao final do período pago."
    )

    class Meta:
        db_table = 'crm_assinatura'
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'
        unique_together = ('usuario', 'plano',)
        # Esta linha (comentada) garantiria que um usuário só tenha uma assinatura
        # para um plano específico ao mesmo tempo.
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

    def registrar_cancelamento(self):
        """
        Este método agora será um dispatcher. Ele não faz a revogação diretamente.
        Será chamado pelo webhook 'customer.subscription.deleted'.
        """
        # Em 'customer.subscription.deleted', Stripe já informa se é cancelamento imediato ou no final do período.
        # Mas como este método é chamado de vários lugares, vamos fazer um dispatcher.
        print(f"Chamando registrar_cancelamento para assinatura {self.id}. Status Stripe: {self.status_assinatura}, CancelAtPeriodEnd: {self.cancel_at_period_end}")
        
        # A lógica de decidir IMEDIATO vs. FIM DO PERÍODO virá do webhook ou do cancelamento manual.
        # Então, o webhook chamará o método mais específico abaixo.
        # Por isso, este método 'registrar_cancelamento' se torna um ponto de entrada.
        # A revogação REAL do acesso será delegada.
        pass # Não faz nada aqui, a lógica real estará nos novos métodos abaixo.

    def marcar_cancelamento_imediato(self):
        """
        Marca a assinatura como 'canceled' e REVOGA O ACESSO IMEDIATAMENTE.
        Usado para trials ou cancelamentos que cortam o acesso na hora.
        """
        self.status_assinatura = 'canceled'
        self.cancel_at_period_end = False # Não está mais esperando o fim do período.
        self.data_expiracao = timezone.now() # Acesso cortado agora.
        self.save()
        self.revogar_acesso() # Chama a lógica para desativar o auth.User.
        print(f"Assinatura {self.id} cancelada e acesso REVOGADO IMEDIATAMENTE.")

    def marcar_cancelamento_ao_final_do_periodo(self):
        """
        Marca a assinatura como 'canceled', mas o acesso continua até o final do período pago.
        A revogação do acesso real será feita por uma tarefa agendada posteriormente.
        """
        self.status_assinatura = 'canceled' # Marca como cancelada
        self.cancel_at_period_end = True # Indica que o acesso só será cortado na data_expiracao.
        # A data_expiracao JÁ DEVE ESTAR DEFINIDA pelo webhook invoice.payment_succeeded ou customer.subscription.updated.
        self.save()
        print(f"Assinatura {self.id} cancelada para o final do período. Acesso continua até {self.data_expiracao}.")
        # NÂO CHAMA revogar_acesso() AQUI. Isso será feito por uma tarefa agendada.

    def revogar_acesso(self):
        """
        Lógica de negócio para desativar o acesso do usuário no seu sistema.
        Este método deve ser chamado apenas quando o acesso precisa ser CORTADO DE FATO.
        """
        print(f"Acesso de {self.usuario.nome_completo} revogado para o plano {self.plano.nome_plano}.")
        if hasattr(self.usuario, 'user') and self.usuario.user:
            self.usuario.user.is_active = False # Desativa o usuário do Django.
            self.usuario.user.save()
            print(f"auth.User '{self.usuario.user.username}' desativado.")
            # Opcional: Remover do grupo "Clientes Assinantes" aqui se for a única maneira de perder acesso.
            self.usuario.user.groups.remove(Group.objects.get(name='Clientes Assinantes'))
            self.usuario.user.save()


    def conceder_acesso(self):
        """
        Lógica para automatizar a concessão de acesso ao sistema para o cliente.
        Esta função será chamada quando a assinatura for 'active' ou 'trialing'.
        """
        print(f"Chamando conceder_acesso para {self.usuario.nome_completo} ({self.usuario.email})")

        auth_user = None
        try:
            auth_user = self.usuario.user 
        except ObjectDoesNotExist:
            auth_user = None
        
        # Gera a senha antes de criar/atualizar o usuário, para que ela possa ser usada no e-mail.
        generated_password =  generate_random_password()# senha_chumbada()
        

        if not auth_user:
            auth_user = User.objects.create_user(
                username=self.usuario.email,
                email=self.usuario.email,
                password=generated_password, # A senha gerada será hashed aqui.
                is_active=True,
                is_staff=True,
                is_superuser=False
            )
            self.usuario.user = auth_user
            self.usuario.save()
            print(f"DEBUG: Novo auth.User criado e vinculado para {self.usuario.email}.")

        else: # Se o 'auth.User' já existia.
            print(f"DEBUG: auth.User existente encontrado para {self.usuario.email}.")
            if not auth_user.is_active:
                auth_user.is_active = True
                print(f"DEBUG: auth.User '{auth_user.username}' reativado.")

            # Define a NOVA senha (ela será hashed) para o usuário existente.
            auth_user.set_password(generated_password)
            auth_user.save()

            if auth_user.is_superuser:
                auth_user.is_superuser = False
                auth_user.save()
                print(f"AVISO: Permissões de staff/superuser para {self.usuario.email} resetadas.")
        
        # 2. Adicionar o 'auth.User' ao grupo "Clientes Assinantes".
        try:
            group = Group.objects.get(name='Clientes Assinantes')
            if not auth_user.groups.filter(name='Clientes Assinantes').exists():
                auth_user.groups.add(group)
                print(f"DEBUG: auth.User '{auth_user.username}' adicionado ao grupo '{group.name}'.")
            else:
                print(f"DEBUG: auth.User '{auth_user.username}' já está no grupo '{group.name}'.")
        except Group.DoesNotExist:
            print("ERRO CRÍTICO: Grupo 'Clientes Assinantes' não encontrado. Crie-o no Admin do Django!")
            return 

        # 3. Enviar E-mail com as Credenciais.
        # A URL de login será um placeholder por enquanto.
        # SUBSTITUA PELA URL REAL DO PORTAL DO CLIENTE (NÃO DO DJANGO ADMIN).
        login_url = "http://seusite.com/portal-cliente/login" 
        
        email_subject = "Suas Credenciais de Acesso ao BarberSites!"
        
        # Prepara o contexto para o template do e-mail.
        email_context = {
            'usuario_nome_completo': self.usuario.nome_completo,
            'usuario_email': self.usuario.email,
            'usuario_senha': generated_password, # A senha em texto plano, APENAS para o envio do email.
                                                    # NUNCA salve a senha em texto plano no banco de dados!
            'login_url': login_url,
        }
        
        # Renderiza o template HTML do e-mail.
        email_html_message = render_to_string('crm/emails/user_credentials.html', email_context)
        
        send_mail(
            subject=email_subject,
            message="", 
            html_message=email_html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.usuario.email],
            fail_silently=False, # Garante que exceções sejam levantadas.
        )
        print(f"DEBUG: E-mail de credenciais enviado para {self.usuario.email}.")
        # --- FIM DA REMOÇÃO TEMPORÁRIA ---
        
        print("DEBUG: Método conceder_acesso concluído.")