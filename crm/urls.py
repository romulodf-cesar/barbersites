# crm/urls.py

from django.urls import path
from . import views # Importa as views do seu próprio aplicativo crm

urlpatterns = [
    # A URL raiz ('') do seu app crm aponta para a view 'index'.
    # O nome 'home' é usado para reverter a URL em outros templates (ex: {% url 'home' %}).
    path('', views.index, name='home'), 
    # NOTA: Removidas as URLs para 'checkout_plano' e 'plano_form' se existiam,
    #       pois o fluxo de checkout Stripe agora é gerenciado pelo app 'payments'.
    # Se você tem outras URLs no crm (que não sejam relacionadas ao Stripe Payments),
    # elas deveriam ser adicionadas aqui.
]






# from django.contrib import admin
# from django.urls import path

# from crm.views import checkout_plano, index, plano_form

# urlpatterns = [
#     # Rota para a página inicial, que lista os planos.
#     # Nome 'index' é uma convenção comum para a página principal.
#     path('', index, name='index'),
#     # Rota para a página de checkout.
#     # Aceita um ID de plano inteiro na URL, que é passado para a view.
#     # Nome 'checkout' é usado na tag {% url %} do template.
#     path('checkout/<int:plano_id>/', checkout_plano, name='checkout'),
#     path('plano/', plano_form, name='plano_form'),
# ]
