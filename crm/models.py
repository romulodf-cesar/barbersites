# models.py
from django.db import models

class Plano(models.Model):
    # O 'id' é gerado automaticamente pelo Django como Primary Key (id).
    # Não precisamos declará-lo explicitamente.

    nome_plano = models.CharField(
        max_length=100,
        verbose_name="Nome do Plano",
        null=False,  # Não permite valores nulos no banco de dados
        blank=False  # Requer que o campo seja preenchido em formulários Django
    )
    valor = models.DecimalField(
        max_digits=10,      # Número total máximo de dígitos (incluindo casas decimais)
        decimal_places=2,   # Número de casas decimais
        verbose_name="Valor",
        null=False,
        blank=False
    )
    descricao = models.TextField(
        verbose_name="Descrição",
        null=True,   # Permite valores nulos no banco de dados
        blank=True   # O campo pode ser deixado em branco em formulários Django
    )

    class Meta:
        db_table = 'crm_plano' # Nome da tabela no banco de dados
        verbose_name = "Plano"
        verbose_name_plural = "Planos"
        # Você pode adicionar outras opções Meta aqui, se necessário,
        # como ordering = ['nome_plano'] para ordenar por nome padrão.

    def __str__(self):
        # Representação textual de um objeto Plano
        return self.nome_plano
    

# Já existe:
# class Plano(models.Model):
#     nome_plano = models.CharField(...)
#     valor = models.DecimalField(...)
#     descricao = models.TextField(...)
#     class Meta:
#         db_table = 'crm_plano'
#     def __str__(self):
#         return self.nome_plano


class Barbearia(models.Model):
    """
    Representa os dados específicos da barbearia.
    """
    nome_barbearia = models.CharField(
        max_length=200,
        verbose_name="Nome da Barbearia",
        null=False,
        blank=False
    )
    endereco = models.CharField(
        max_length=255,
        verbose_name="Endereço Completo",
        null=False,
        blank=False
    )
    cidade = models.CharField(
        max_length=100,
        verbose_name="Cidade",
        null=False,
        blank=False
    )
    estado = models.CharField(
        max_length=2,  # Ex: SP, RJ, MG
        verbose_name="Estado (UF)",
        null=False,
        blank=False
    )
    cep = models.CharField(
        max_length=9,  # Formato 00000-000
        verbose_name="CEP",
        null=False,
        blank=False
    )

    class Meta:
        db_table = 'crm_barbearia'
        verbose_name = "Barbearia"
        verbose_name_plural = "Barbearias"

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
        max_length=200,
        verbose_name="Nome Completo",
        null=False,
        blank=False
    )
    email = models.EmailField(
        unique=True, # Garante que cada email seja único
        verbose_name="Email",
        null=False,
        blank=False
    )
    telefone = models.CharField(
        max_length=20, # Ex: (XX) XXXX-XXXX ou (XX) XXXXX-XXXX
        verbose_name="Telefone",
        null=False,
        blank=False
    )
    
    # Campo para aceitação de termos e notificações
    aceite_termos = models.BooleanField(default=False, verbose_name="Aceitou Termos de Uso")
    receber_notificacoes = models.BooleanField(default=False, verbose_name="Deseja receber notificações")

    class Meta:
        db_table = 'crm_usuario'
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return self.nome_completo


class Assinatura(models.Model):
    """
    Representa a relação entre um Usuário, um Plano e uma Barbearia,
    contendo o status do pagamento e o tipo de acesso.
    """
    # Opções para o status da assinatura/pagamento
    STATUS_PAGAMENTO_CHOICES = [
        ('pendente', 'Pagamento Pendente'),
        ('pago', 'Pago'),
        ('cancelado', 'Cancelado'),
        ('expirado', 'Expirado'),
    ]

    # Opções para o status do usuário (tipo de acesso)
    STATUS_USUARIO_CHOICES = [
        ('padrao', 'Usuário Padrão'),
        ('premium', 'Usuário Premium'), # Exemplo: Pode ter planos 'Premium'
        ('admin', 'Administrador'),     # Exemplo: Se for um admin da barbearia
    ]

    # Chave estrangeira para o Usuário que fez a assinatura
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE, # Se o usuário for deletado, a assinatura também é
        related_name='assinaturas',
        verbose_name="Usuário"
    )

    # Chave estrangeira para o Plano contratado
    plano = models.ForeignKey(
        Plano,
        on_delete=models.PROTECT, # Não permite deletar um plano se houver assinaturas ativas
        related_name='assinaturas',
        verbose_name="Plano Contratado"
    )

    # Chave estrangeira para a Barbearia associada a esta assinatura
    # Note: Um usuário pode ter múltiplas barbearias se for o caso,
    # ou uma barbearia pode ser gerenciada por múltiplos usuários.
    # Neste caso, cada assinatura está ligada a UMA Barbearia.
    barbearia = models.ForeignKey(
        Barbearia,
        on_delete=models.CASCADE, # Se a barbearia for deletada, as assinaturas dela também
        related_name='assinaturas',
        verbose_name="Barbearia Associada"
    )

    status_pagamento = models.CharField(
        max_length=20,
        choices=STATUS_PAGAMENTO_CHOICES,
        default='pendente',
        verbose_name="Status do Pagamento"
    )
    
    status_usuario = models.CharField(
        max_length=20,
        choices=STATUS_USUARIO_CHOICES,
        default='padrao',
        verbose_name="Status do Usuário"
    )

    data_inicio = models.DateTimeField(
        auto_now_add=True, # Registra a data e hora de criação da assinatura
        verbose_name="Data de Início"
    )
    data_expiracao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data de Expiração"
    )
    
    # Campo para armazenar o ID da transação do gateway de pagamento
    id_transacao_pagamento = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True, # A ID da transação deve ser única
        verbose_name="ID da Transação de Pagamento"
    )

    class Meta:
        db_table = 'crm_assinatura'
        verbose_name = "Assinatura"
        verbose_name_plural = "Assinaturas"
        # Garante que um usuário só tenha uma assinatura para um plano específico
        # em um determinado momento para a mesma barbearia.
        # Pode ser ajustado dependendo da lógica de negócio (ex: permitir várias assinaturas)
        # unique_together = ('usuario', 'plano', 'barbearia',) 

    def __str__(self):
        return f"Assinatura de {self.usuario.nome_completo} para {self.plano.nome_plano} ({self.status_pagamento})"

    # Exemplo de método para atualizar o status
    def marcar_como_pago(self, transacao_id=None):
        self.status_pagamento = 'pago'
        if transacao_id:
            self.id_transacao_pagamento = transacao_id
        # Define a data de expiração com base no plano (ex: 30 dias se for mensal)
        # Requer lógica adicional para calcular a expiração
        # from datetime import timedelta
        # self.data_expiracao = self.data_inicio + timedelta(days=30)
        self.save()

    def marcar_como_cancelado(self):
        self.status_pagamento = 'cancelado'
        self.save()