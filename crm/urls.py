# crm/urls.py

from django.urls import path
from . import views # Importa as views do seu próprio aplicativo crm

urlpatterns = [
    # A URL raiz ('') do seu app crm aponta para a view 'index'.
    # O nome 'home' é usado para reverter a URL em outros templates (ex: {% url 'home' %}).
    path('', views.index, name='home'), 
    # Se você tem outras URLs no crm (que não sejam relacionadas ao Stripe Payments),
    # elas deveriam ser adicionadas aqui.
]