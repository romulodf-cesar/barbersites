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