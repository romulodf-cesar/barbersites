from django.contrib import admin

from .models import Plano  # Importe o seu modelo Plano


@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = (
        'nome_plano',
        'valor',
        'descricao_curta',
    )   # Campos que aparecem na lista
    list_filter = ('nome_plano',)   # Filtros na barra lateral
    search_fields = ('nome_plano', 'descricao')   # Campos para pesquisa
    # fields = ('nome_plano', 'valor', 'descricao') # Ordem dos campos na página de edição/criação

    # Método para exibir uma versão curta da descrição na list_display
    def descricao_curta(self, obj):
        return (
            (obj.descricao[:50] + '...')
            if len(obj.descricao) > 50
            else obj.descricao
        )

    descricao_curta.short_description = 'Descrição'   # Nome da coluna no admin
