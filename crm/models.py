from django.db import models

# seu_app/models/plano.py

from django.db import models # Importa o módulo models do Django para definir a classe de modelo.

class Plano(models.Model):
    """
    Modelo Django que representa um 'Plano' no sistema da barbearia,
    conforme o Diagrama de Entidade-Relacionamento (DER) fornecido.
    Um plano pode ser um tipo de serviço, um pacote, ou uma assinatura.
    """
    # O campo 'id' (Primary Key) é automaticamente criado pelo Django
    # como um AutoField (inteiro auto-incrementável) para cada modelo.
    # Não é necessário declará-lo explicitamente, a menos que você queira
    # um tipo de chave primária diferente.

    nome_plano = models.CharField(
        max_length=100,  # Define o tamanho máximo da string para o nome do plano.
                         # Escolha um tamanho razoável para nomes de planos (ex: "Corte Simples", "Pacote Barba e Cabelo Premium").
        verbose_name="Nome do Plano" # Um nome mais amigável para exibição em interfaces de usuário, como o admin do Django.
    )
    valor = models.DecimalField(
        max_digits=10,   # Define o número total máximo de dígitos que o valor pode ter.
                         # Por exemplo, 10 dígitos com 2 casas decimais permite valores até 99.999.999,99.
        decimal_places=2,# Define o número de casas decimais a serem armazenadas. Essencial para valores monetários.
        verbose_name="Valor" # Nome amigável para o campo.
    )
    descricao = models.TextField(
        blank=True,      # 'blank=True' permite que o campo seja deixado em branco nos formulários Django.
                         # Isso significa que o usuário não é obrigado a preencher este campo.
        null=True,       # 'null=True' permite que o campo no banco de dados seja NULL (vazio).
                         # É importante usar null=True com blank=True para campos opcionais não-caractere.
        verbose_name="Descrição do Plano" # Nome amigável para o campo.
    )

    def __str__(self):
        """
        Método mágico que retorna uma representação em string do objeto Plano.
        Isso é muito útil no painel de administração do Django e ao depurar,
        pois mostra um nome legível para cada instância do modelo.
        """
        return self.nome_plano # Retorna o nome do plano para identificar o objeto.

    class Meta:
        """
        A classe Meta interna de um modelo é usada para definir metadados do modelo,
        ou seja, "coisas sobre o seu modelo".
        """
        verbose_name = "Plano"         # Nome singular para o modelo, usado em interfaces como o admin.
        verbose_name_plural = "Planos" # Nome plural para o modelo, também usado em interfaces.
        ordering = ['valor', 'nome_plano'] # Define a ordem padrão dos registros quando consultados.
                                         # Neste caso, ordena primeiro pelo 'valor' (crescente) e,
                                         # se os valores forem iguais, pelo 'nome_plano' (alfabético).
