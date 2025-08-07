from rest_framework import serializers
from crm.models import Assinatura, Plano, Barbearia, Usuario

# Serializer para o modelo Usuario
class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'

# Serializer para o modelo Plano
class PlanoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plano
        fields = '__all__'

# Serializer para o modelo Barbearia
class BarbeariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barbearia
        fields = '__all__'

# Serializer principal para o endpoint de status.
class AssinaturaStatusSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    plano = PlanoSerializer(read_only=True)
    barbearia = BarbeariaSerializer(read_only=True)
    
    class Meta:
        model = Assinatura
        fields = [
            'stripe_subscription_id',
            'status_assinatura',
            'data_inicio',
            'data_expiracao',
            'trial_end',
            'cancel_at_period_end',
            'usuario',
            'plano',
            'barbearia',
        ]

# Serializer para o endpoint de cancelamento.
class CancelamentoSerializer(serializers.Serializer):
    stripe_subscription_id = serializers.CharField(
        max_length=100,
        required=True,
        help_text="O ID da assinatura do Stripe a ser cancelada."
    )
