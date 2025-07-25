from django.contrib import admin
from django.urls import path

from crm.views import checkout_plano, index, plano_form

urlpatterns = [
    # Rota para a página inicial, que lista os planos.
    # Nome 'index' é uma convenção comum para a página principal.
    path('', index, name='index'),
    # Rota para a página de checkout.
    # Aceita um ID de plano inteiro na URL, que é passado para a view.
    # Nome 'checkout' é usado na tag {% url %} do template.
    path('checkout/<int:plano_id>/', checkout_plano, name='checkout'),
    path('plano/', plano_form, name='plano_form'),
]
