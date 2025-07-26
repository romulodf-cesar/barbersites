# crm/tests.py
from django.test import TestCase
from crm.models import Plano

class PlanoModelTest(TestCase):
    def setUp(self):
        # Quando você usa Plano.objects.create(), o objeto já é salvo no banco de dados.
        # Ele será salvo no seu banco de dados de TESTE (barbearia_db_test).
        self.plano = Plano.objects.create(
            nome_plano='Plano Básico',
            valor=10,
            descricao='Plano básico com recursos limitados.'
        )

    def test_plano_creation_and_database_insertion(self):
        """
        Testa a criação de um Plano e a sua correta inserção no banco de dados.
        """
        # Esta linha verifica se HÁ EXATAMENTE 1 OBJETO do tipo Plano no banco de dados.
        # Se 1 objeto foi inserido com sucesso pelo .create() no setUp, este teste passa.
        self.assertEqual(Plano.objects.count(), 1)

        # Esta linha tenta recuperar o objeto do banco de dados usando sua chave primária (PK).
        # Se o objeto foi inserido e pode ser lido de volta, esta linha funciona.
        plano_do_banco = Plano.objects.get(pk=self.plano.pk)

        # Estas linhas verificam se os dados recuperados do banco são os mesmos que você inseriu.
        self.assertEqual(plano_do_banco.nome_plano, 'Plano Básico')
        self.assertEqual(plano_do_banco.valor, 10)
        self.assertEqual(plano_do_banco.descricao, 'Plano básico com recursos limitados.')

# Como executar esse teste no Visual Studio Code
# Para executar os testes,
# você pode usar o terminal integrado do Visual Studio Code.
# Navegue até o diretório do seu projeto Django e execute:
# python manage.py test crm.tests.PlanoModelTest
# Isso executará os testes definidos na classe PlanoModelTest.  
# Você verá a saída no terminal, indicando se os testes passaram ou falharam.
# Se você quiser executar todos os testes do aplicativo `crm`, basta usar:
# python manage.py test crm
# Isso executará todos os testes definidos no módulo `crm.tests`.