from django.urls import path
from .views import AssinaturaStatusView, CancelarAssinaturaView, MockProvisionarInstanciaView

urlpatterns = [
    path('v1/assinatura-status/<str:stripe_subscription_id>/', AssinaturaStatusView.as_view(), name='assinatura-status'),
    path('v1/cancelar-assinatura/', CancelarAssinaturaView.as_view(), name='cancelar-assinatura'),
    
    # URL para o mock do endpoint de provisionamento de instância
    path('v1/provisionar-instancia/', MockProvisionarInstanciaView.as_view(), name='mock-provisionar-instancia'),
]