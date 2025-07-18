from django.contrib import admin
from django.urls import path
from . import views


urlpatterns = [
    # Rota para a página inicial, que lista os planos.
    # Nome 'home' é uma convenção comum para a página principal.
    path('', views.index, name='home'), 
    # Rota para a página de checkout.
    # Aceita um ID de plano inteiro na URL, que é passado para a view.
    # Nome 'checkout' é usado na tag {% url %} do template.
    path('checkout/<int:plano_id>/', views.checkout_plano,name='checkout'),
    path('admin/', admin.site.urls),
]