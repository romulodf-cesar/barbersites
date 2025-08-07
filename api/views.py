from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404
from crm.models import Assinatura
from api.serializers import AssinaturaStatusSerializer, CancelamentoSerializer
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

class AssinaturaStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Assinaturas'],
        summary='Consulta o status de uma assinatura do Stripe.',
        description='Endpoint para o Sistema de Templates verificar o status de pagamento de um cliente usando o ID da assinatura do Stripe.',
        responses={
            200: AssinaturaStatusSerializer,
            404: {'description': 'Assinatura não encontrada.'},
            401: {'description': 'Não autenticado.'},
        }
    )
    def get(self, request, stripe_subscription_id, *args, **kwargs):
        try:
            assinatura = Assinatura.objects.get(stripe_subscription_id=stripe_subscription_id)
            serializer = AssinaturaStatusSerializer(assinatura)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Assinatura.DoesNotExist:
            return Response(
                {"detail": "Assinatura não encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": f"Ocorreu um erro inesperado: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CancelarAssinaturaView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Assinaturas'],
        summary='Solicita o cancelamento de uma assinatura do Stripe.',
        description='Endpoint para o Sistema de Templates solicitar o cancelamento de uma assinatura, que é processado no CRM. O tipo de cancelamento (imediato ou no final do período) é determinado automaticamente pelo plano.',
        request=CancelamentoSerializer,
        responses={
            200: {'description': 'Cancelamento solicitado com sucesso.'},
            400: {'description': 'Dados inválidos.'},
            404: {'description': 'Assinatura não encontrada.'},
            401: {'description': 'Não autenticado.'},
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = CancelamentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        stripe_subscription_id = serializer.validated_data['stripe_subscription_id']
        
        try:
            # 1. Busca a assinatura localmente para obter o plano
            assinatura = Assinatura.objects.get(stripe_subscription_id=stripe_subscription_id)
            
            # 2. Determina a lógica de cancelamento baseada no plano
            # Se o plano tem período de teste, o cancelamento deve ser imediato.
            # Caso contrário, o cancelamento é no final do período pago.
            cancel_at_period_end = assinatura.plano.trial_period_days == 0
            
            # 3. Faz a chamada de API do Stripe com a lógica correta
            if cancel_at_period_end:
                # Modifica a assinatura para que ela seja cancelada no final do período
                stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=True
                )
                print(f"DEBUG: Assinatura {assinatura.id} marcada para cancelamento ao final do período.")
            else:
                # Deleta a assinatura imediatamente
                stripe.Subscription.delete(stripe_subscription_id)
                print(f"DEBUG: Assinatura {assinatura.id} deletada/cancelada imediatamente.")
            
            # 4. Retorna a resposta, mas sem atualizar o banco de dados localmente.
            # Os webhooks 'customer.subscription.updated' ou 'customer.subscription.deleted'
            # se encarregarão de fazer essa atualização de forma segura.
            return Response({"message": "Cancelamento solicitado com sucesso. Aguardando confirmação do webhook do Stripe."}, status=status.HTTP_200_OK)

        except Assinatura.DoesNotExist:
            return Response(
                {"detail": "Assinatura não encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )
        except stripe.error.StripeError as e:
            return Response(
                {"detail": f"Erro na API do Stripe: {e}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": f"Ocorreu um erro inesperado: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MockProvisionarInstanciaView(APIView):
    """
    Mock do endpoint do orquestrador de templates.
    Apenas para fins de teste.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Mocks'],
        summary='[MOCK] Simula o provisionamento de uma nova instância.',
        description='Este endpoint recebe o pedido de provisionamento do CRM e retorna uma URL de teste. Use-o para testar o fluxo de concessão de acesso sem o sistema de templates real.',
        request={'type': 'object', 'properties': {'barbearia_id': {'type': 'integer'}, 'barbearia_nome': {'type': 'string'}, 'usuario_email': {'type': 'string'}, 'stripe_subscription_id': {'type': 'string'}}},
        responses={200: {'description': 'Mock de resposta de sucesso', 'schema': {'type': 'object', 'properties': {'instance_url': {'type': 'string'}}}}}
    )
    def post(self, request, *args, **kwargs):
        # Apenas para depuração, imprime o payload que o seu código enviou
        print(f"MOCK: Requisição de provisionamento de instância recebida com payload: {request.data}")
        
        # O orquestrador mockado retorna uma URL de teste.
        # Use um ID dinâmico ou estático aqui, o importante é que seja uma URL.
        barbearia_id = request.data.get('barbearia_id', 'mocked-id')
        mock_url = f"http://instancia-mockada-{barbearia_id}.templates.com.br"
        
        return Response({'instance_url': mock_url}, status=status.HTTP_200_OK)
