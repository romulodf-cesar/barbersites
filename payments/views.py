# payments/views.py

# Importações necessárias
import stripe # Biblioteca oficial do Stripe para Python
import json # Para trabalhar com dados JSON (recebidos do frontend)
from django.conf import settings # Para acessar configurações do seu settings.py (chaves do Stripe)
from django.shortcuts import render, get_object_or_404, redirect # Funções utilitárias do Django
from django.http import JsonResponse, HttpResponse # Para retornar respostas HTTP e JSON
from django.views.decorators.csrf import csrf_exempt # Decorador para desativar proteção CSRF em views específicas
from django.urls import reverse # Para gerar URLs dinamicamente
# IMPORTANTE: Importa os modelos do app 'crm', pois são eles que guardam os dados de Plano, Usuário, Barbearia e Assinatura
from crm.models import Plano, Usuario, Barbearia, Assinatura
from datetime import datetime, timezone # Para trabalhar com datas e fusos horários (necessário para timestamps do Stripe)

# Configura a chave secreta do Stripe.
# Essa chave autentica suas requisições para a API do Stripe no backend.
# settings.STRIPE_SECRET_KEY é lido do seu arquivo .env via settings.py.
stripe.api_key = settings.STRIPE_SECRET_KEY

# ----------------------------------------------------------------------
# 1. View para exibir a lista de planos na página inicial
# ----------------------------------------------------------------------
def list_plans(request):
    """
    Lista todos os planos disponíveis do seu modelo 'Plano' (do app crm)
    e os exibe em um template HTML.
    """
    # Busca todos os objetos Plano no banco de dados e os ordena pelo valor.
    planos = Plano.objects.all().order_by('valor')
    
    # Prepara o contexto que será passado para o template.
    context = {
        'planos': planos, # A lista de planos para o loop no HTML
        # A chave pública do Stripe é passada para o frontend, pois é segura e usada pelo Stripe.js.
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY
    }
    # Renderiza o template 'payments/list_plans.html' com os dados do contexto.
    # Este template deve estar em 'sua_pasta_do_projeto/templates/payments/list_plans.html'.
    return render(request, 'payments/list_plans.html', context)

# ----------------------------------------------------------------------
# 2. View para criar uma sessão de checkout no Stripe
#    Esta view é chamada pelo JavaScript do frontend (do checkout.html).
# ----------------------------------------------------------------------
@csrf_exempt # Desativa a proteção CSRF para esta view. Necessário porque a requisição
             # é via JavaScript (Fetch API) e não de um formulário Django padrão.
             # O CSRF é gerenciado manualmente no JavaScript do template.
def create_checkout_session(request, plano_pk):
    """
    Cria uma sessão de checkout no Stripe para um plano específico.
    Recebe o ID do plano (plano_pk) e dados do usuário/barbearia do frontend.
    """
    # Tenta obter o objeto Plano do banco de dados pelo seu ID (pk).
    # Se o plano não for encontrado, retorna uma página 404.
    plano = get_object_or_404(Plano, pk=plano_pk)

    # Processa apenas requisições POST, que são as esperadas do frontend.
    if request.method == 'POST':
        # Verifica se o plano local tem um ID de preço do Stripe configurado.
        # Se não tiver, o Stripe não saberá o que cobrar.
        if not plano.stripe_price_id:
            return JsonResponse({'error': 'Este plano não tem um ID de preço configurado no Stripe.'}, status=400)

        try:
            # NOVO: Parseia os dados JSON enviados pelo frontend no corpo da requisição.
            # Estes dados contêm informações sobre o usuário e a barbearia.
            data = json.loads(request.body)
            usuario_data = data.get('usuario_data')
            barbearia_data = data.get('barbearia_data')

            # Validação básica para garantir que os dados necessários foram enviados.
            if not usuario_data or not barbearia_data:
                return JsonResponse({'error': 'Dados de usuário ou barbearia ausentes.'}, status=400)

            # 1. Processar/Salvar/Obter Usuário:
            # Tenta encontrar um Usuário existente pelo email. Se não existir, um novo é criado.
            usuario, created_user = Usuario.objects.get_or_create(
                email=usuario_data['email'],
                defaults={ # Valores padrão se um novo Usuário for criado
                    'nome_completo': usuario_data['nome_completo'],
                    'telefone': usuario_data['telefone'],
                    'aceite_termos': usuario_data.get('aceite_termos', False), # Usa .get para valor padrão se não existir
                    'receber_notificacoes': usuario_data.get('receber_notificacoes', False)
                }
            )
            # Observação: Se o usuário já existia mas algum dado novo foi passado,
            # você pode implementar lógica de atualização aqui, se necessário.
            
            # 2. Processar/Salvar/Obter Barbearia:
            # Tenta encontrar uma Barbearia existente pelo nome. Se não existir, uma nova é criada.
            barbearia, created_barber = Barbearia.objects.get_or_create(
                nome_barbearia=barbearia_data['nome_barbearia'],
                defaults={ # Valores padrão se uma nova Barbearia for criada
                    'endereco': barbearia_data['endereco'],
                    'cidade': barbearia_data['cidade'],
                    'estado': barbearia_data['estado'],
                    'cep': barbearia_data['cep']
                }
            )
            # Observação: Lógica de atualização similar à do Usuário pode ser aplicada aqui.
            
            # Pega o ID de cliente do Stripe (stripe_customer_id) associado ao Usuário, se existir.
            # Este ID é usado para vincular o cliente no Stripe ao seu Usuário local.
            customer_stripe_id = usuario.stripe_customer_id

            # Prepara os parâmetros para criar a sessão de checkout no Stripe.
            session_params = {
                'line_items': [ # Itens que o Stripe Checkout exibirá e cobrará
                    {
                        'price': plano.stripe_price_id, # ID do preço do Stripe associado ao plano Django
                        'quantity': 1, # Apenas uma unidade do plano
                    },
                ],
                'mode': 'subscription', # Define o modo da sessão como 'assinatura' (pagamento recorrente)
                # URLs para onde o usuário será redirecionado após a conclusão/cancelamento no Stripe.
                'success_url': request.build_absolute_uri(reverse('payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
                'cancel_url': request.build_absolute_uri(reverse('payment_cancel')),
            }

            # Lógica para passar o cliente para o Stripe:
            # Se já temos um customer_stripe_id para o usuário, usamos ele.
            # Isso é bom para rastrear um mesmo cliente no Stripe ao longo do tempo (evitar duplicatas de cliente no Stripe).
            if customer_stripe_id:
                session_params['customer'] = customer_stripe_id
            # Caso contrário (se for a primeira compra desse usuário), passamos o e-mail.
            # O Stripe tentará encontrar um cliente existente com esse e-mail ou criará um novo.
            else:
                session_params['customer_email'] = usuario.email

            # Adiciona o período de teste gratuito se o plano tiver.
            if plano.trial_period_days > 0:
                session_params['subscription_data'] = {
                    'trial_period_days': plano.trial_period_days,
                }
                print(f"Criando sessão de assinatura para o plano '{plano.nome_plano}' com {plano.trial_period_days} dias de teste gratuito.")

            # Cria a sessão de checkout no Stripe. Esta chamada comunica-se com a API do Stripe.
            # A resposta contém o ID da sessão de checkout, que será usado pelo JavaScript.
            checkout_session = stripe.checkout.Session.create(**session_params)

            # Retorna o ID da sessão de checkout para o frontend em formato JSON.
            # O JavaScript do frontend usará este ID para redirecionar o usuário para a página do Stripe.
            return JsonResponse({'id': checkout_session.id})
        
        # Captura qualquer exceção que ocorra durante a criação da sessão e retorna um erro 400.
        except Exception as e:
            print(f"ERRO ao criar sessão de checkout: {e}") # Loga o erro no terminal
            return JsonResponse({'error': str(e)}, status=400)

# ----------------------------------------------------------------------
# 3. View para a página de sucesso após o pagamento/assinatura
# ----------------------------------------------------------------------
def payment_success(request):
    """
    Exibe uma página de sucesso após o usuário concluir o checkout no Stripe.
    Recebe o 'session_id' via parâmetro GET na URL.
    """
    session_id = request.GET.get('session_id')
    session = None
    # Se um session_id foi fornecido na URL, tenta recuperar a sessão do Stripe.
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        # Captura erros específicos da API do Stripe.
        except stripe.error.StripeError as e:
            # Se a sessão não puder ser recuperada, renderiza uma página de erro.
            return render(request, 'payments/error.html', {'message': f"Erro ao recuperar sessão: {e}"})
    # Renderiza a página de sucesso, passando os detalhes da sessão (se recuperada).
    # O template deve estar em 'sua_pasta_do_projeto/templates/payments/success.html'.
    return render(request, 'payments/success.html', {'session': session})

# ----------------------------------------------------------------------
# 4. View para a página de cancelamento do pagamento/assinatura
# ----------------------------------------------------------------------
def payment_cancel(request):
    """
    Exibe uma página de cancelamento se o usuário não concluir o checkout no Stripe.
    """
    # Renderiza a página de cancelamento.
    # O template deve estar em 'sua_pasta_do_projeto/templates/payments/cancel.html'.
    return render(request, 'payments/cancel.html')

# ----------------------------------------------------------------------
# 5. View para o Webhook do Stripe (MUITO IMPORTANTE para confirmar pagamentos/assinaturas)
# ----------------------------------------------------------------------
@csrf_exempt # Desativa a proteção CSRF. Essencial para webhooks, pois as requisições vêm
             # diretamente dos servidores do Stripe e não do seu navegador.
             # A segurança é garantida pela assinatura do webhook do Stripe.
def stripe_webhook(request):
    """
    Processa eventos de webhook enviados pelo Stripe.
    É aqui que a lógica de negócios crucial é executada (ex: atualizar status de assinatura).
    """
    payload = request.body # O corpo da requisição (os dados do evento Stripe)
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE') # O cabeçalho de assinatura do Stripe

    # Tenta construir o objeto de evento Stripe, verificando sua autenticidade.
    # Se a assinatura não for válida (STRIPE_WEBHOOK_SECRET incorreta ou payload adulterado),
    # uma exceção é levantada.
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    # Captura erros de payload inválido (corpo da requisição mal-formado).
    except ValueError as e:
        print(f"Erro no Webhook: Payload inválido: {e}")
        return HttpResponse(status=400) # Retorna 400 Bad Request
    # Captura erros de assinatura inválida.
    except stripe.error.SignatureVerificationError as e:
        print(f"Erro no Webhook: Assinatura inválida: {e}")
        return HttpResponse(status=400) # Retorna 400 Bad Request
    # Captura quaisquer outras exceções durante a construção do evento.
    except Exception as e:
        print(f"Erro inesperado na construção do evento webhook: {e}")
        return HttpResponse(status=400) # Retorna 400 Bad Request


    # ------------------------------------------------------------------
    # Processamento dos Eventos de Webhook (Lógica de Negócios)
    # ------------------------------------------------------------------

    # Evento: Nova sessão de checkout concluída (criação de assinatura)
    # Este evento é disparado quando o cliente finaliza o checkout no Stripe.
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object'] # O objeto 'session' contém detalhes da sessão de checkout
        print(f"Webhook: Checkout Session Completed - Session ID: {session.id}")

        # Se a sessão é para uma assinatura (nosso caso para Planos)
        if session.mode == 'subscription':
            subscription_id = session.subscription # O ID da assinatura criada no Stripe
            customer_id = session.customer # O ID do cliente no Stripe
            customer_email = session.customer_details.email if session.customer_details and session.customer_details.email else None
            customer_name = session.customer_details.name if session.customer_details and session.customer_details.name else None

            # --- CORREÇÃO FINAL E ROBUSTA para obter stripe_price_id ---
            # Para assinaturas, o 'price_id' nem sempre vem direto no payload da sessão.
            # A forma mais confiável é listar os itens de linha da sessão.
            stripe_price_id = None
            if subscription_id: # Só tenta se tiver um subscription_id para buscar
                try:
                    # 1. Tentar listar os line items da sessão de checkout.
                    # Esta é a forma mais recomendada pelo Stripe para este cenário.
                    line_items_from_session = stripe.checkout.Session.list_line_items(session.id)
                    
                    # Verifica se a lista de itens não está vazia e tem dados.
                    if line_items_from_session and line_items_from_session.data:
                        first_item = line_items_from_session.data[0] # Pega o primeiro item de linha (assumimos 1 plano por assinatura)
                        # Verifica se o item tem o atributo 'price' e se não é nulo.
                        if hasattr(first_item, 'price') and first_item.price:
                            stripe_price_id = first_item.price.id # Extrai o ID do preço do Stripe
                        else:
                            print(f"ERRO DEBUG: Item de linha da sessão {session.id} não possui atributo 'price'.")
                            # Se não encontrou o price aqui, levanta uma exceção para o erro ser capturado.
                            raise Exception("Price attribute missing from line item after listing.")
                    else:
                        print(f"ERRO DEBUG: Nenhum item de linha encontrado para sessão {session.id} via list_line_items.")
                        # Se a lista de itens da sessão está vazia, levanta uma exceção.
                        raise Exception("No line items found for checkout session after listing.")

                # Captura erros específicos da API do Stripe durante a chamada.
                except stripe.error.StripeError as e:
                    print(f"ERRO WEBHOOK: Falha ao obter line_items da sessão {session.id}: {e}")
                    return JsonResponse({'status': 'error', 'message': f"Falha ao obter line_items: {e}"}, status=500) # Retorna 500 para Stripe re-tentar
                # Captura quaisquer outras exceções inesperadas durante a extração do price_id.
                except Exception as e:
                    print(f"ERRO WEBHOOK INESPERADO ao obter price_id para {session.id}: {e}")
                    print(f"Detalhes do erro 'e': {str(e)}") # Útil para depuração
                    return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
            # Se, por algum motivo, o stripe_price_id ainda não foi encontrado, retorna 400.
            if not stripe_price_id:
                print("ERRO WEBHOOK: stripe_price_id não encontrado na sessão de checkout. Impossível vincular ao plano local.")
                return JsonResponse({'status': 'error', 'message': 'stripe_price_id missing'}, status=400)

            try:
                # 1. Encontrar ou criar o Usuário no seu banco de dados.
                usuario, created_user = Usuario.objects.get_or_create(
                    email=customer_email,
                    defaults={
                        'nome_completo': customer_name if customer_name else customer_email,
                        'telefone': 'N/A' # Pode ser preenchido por um formulário mais completo
                    }
                )
                if created_user:
                    print(f"Usuário criado: {usuario.email}")

                # 2. Atualizar o stripe_customer_id do Usuário, se ele não tiver.
                if not usuario.stripe_customer_id:
                    usuario.stripe_customer_id = customer_id
                    usuario.save()
                    print(f"stripe_customer_id '{customer_id}' associado ao usuário '{usuario.email}'.")

                # 3. Encontrar o Plano correspondente no seu banco de dados.
                plano = Plano.objects.get(stripe_price_id=stripe_price_id)

                # 4. Obter uma Barbearia (assumindo uma barbearia padrão para o cenário "coringa").
                # Em um cenário real, a Barbearia seria associada de forma mais complexa.
                barbearia = Barbearia.objects.first()
                if not barbearia:
                    print("AVISO: Nenhuma barbearia encontrada. Não foi possível criar a assinatura localmente.")
                    return JsonResponse({'status': 'success', 'message': 'No barbershop found.'})

                # 5. Criar ou atualizar a Assinatura no seu banco de dados.
                assinatura, created_sub = Assinatura.objects.get_or_create(
                    stripe_subscription_id=subscription_id, # Usamos o ID do Stripe como chave principal
                    defaults={ # Valores padrão para um novo registro de Assinatura
                        'usuario': usuario,
                        'plano': plano,
                        'barbearia': barbearia,
                        'status_assinatura': 'pendente', # Será atualizado pelo status real do Stripe
                    }
                )

                if created_sub:
                    print(f"Assinatura localmente criada: {assinatura.id} para {usuario.email}.")
                else:
                    print(f"Assinatura local existente atualizada: {assinatura.id} para {usuario.email}.")

                # 6. Recuperar o objeto de assinatura completo do Stripe para obter o status e as datas precisas.
                stripe_subscription_obj = stripe.Subscription.retrieve(subscription_id)

                # --- CORREÇÃO FINAL PARA DATAS (current_period_start, trial_end, etc.) ---
                # Garante que os valores de timestamp não são None antes de passar para datetime.fromtimestamp.
                # Se o timestamp for None ou 0, a variável _dt será None.
                current_period_start_dt = datetime.fromtimestamp(stripe_subscription_obj.current_period_start, tz=timezone.utc) if stripe_subscription_obj.current_period_start else None
                current_period_end_dt = datetime.fromtimestamp(stripe_subscription_obj.current_period_end, tz=timezone.utc) if stripe_subscription_obj.current_period_end else None
                trial_end_dt = datetime.fromtimestamp(stripe_subscription_obj.trial_end, tz=timezone.utc) if stripe_subscription_obj.trial_end else None

                # 7. Atualizar o status e as datas da assinatura localmente.
                assinatura.set_status_and_dates(
                    status=stripe_subscription_obj.status, # Pega o status real do Stripe (trialing, active, etc.)
                    current_period_start=current_period_start_dt,
                    current_period_end=current_period_end_dt,
                    trial_end=trial_end_dt
                )
                print(f"Assinatura {assinatura.id} status inicial: {assinatura.status_assinatura}.")
                
                # 8. Conceder ou revogar acesso com base no status da assinatura.
                if assinatura.status_assinatura == 'trialing' or assinatura.status_assinatura == 'active':
                    assinatura.conceder_acesso()
                else:
                    assinatura.revogar_acesso() # Caso o status inicial já não seja ativo/trialing

            # Captura erro se o Plano do Stripe não for encontrado no Django.
            except Plano.DoesNotExist:
                print(f"ERRO WEBHOOK: Plano com stripe_price_id {stripe_price_id} não encontrado localmente.")
                return JsonResponse({'status': 'error', 'message': 'Plano not found'}, status=400)
            # Captura qualquer outra exceção inesperada durante o processamento da assinatura.
            except Exception as e:
                print(f"ERRO WEBHOOK INESPERADO ao processar criação/atualização da assinatura: {e}")
                print(f"Detalhes do erro 'e': {str(e)}") # Adicionado para depuração
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


    # Evento: Status da assinatura atualizado (incluindo término de trial, troca de plano, etc.)
    # Este evento é muito importante para manter o status da assinatura localmente sincronizado.
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object'] # Objeto da assinatura do Stripe
        print(f"Webhook: Subscription Updated - ID: {subscription.id} - Status: {subscription.status}")

        try:
            # Tenta encontrar a assinatura local pelo ID do Stripe.
            assinatura = Assinatura.objects.get(stripe_subscription_id=subscription.id)

            # --- CORREÇÃO FINAL PARA DATAS (current_period_start, trial_end, etc.) ---
            # Garante que os valores de timestamp não são None antes da conversão.
            current_period_start_dt = datetime.fromtimestamp(subscription.current_period_start, tz=timezone.utc) if subscription.current_period_start else None
            current_period_end_dt = datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc) if subscription.current_period_end else None
            trial_end_dt = datetime.fromtimestamp(subscription.trial_end, tz=timezone.utc) if subscription.trial_end else None

            # Atualiza o status e as datas da assinatura localmente.
            assinatura.set_status_and_dates(
                status=subscription.status,
                current_period_start=current_period_start_dt,
                current_period_end=current_period_end_dt,
                trial_end=trial_end_dt
            )

            # Lógica para conceder ou revogar acesso com base no novo status.
            if assinatura.status_assinatura == 'active':
                print(f"Assinatura {assinatura.id} ativada/renovada. Acesso concedido/mantido.")
                assinatura.conceder_acesso()
            elif assinatura.status_assinatura == 'past_due' or subscription.status == 'unpaid':
                print(f"Assinatura {assinatura.id} vencida/não paga. Considerar suspender acesso.")
                assinatura.revogar_acesso()
            elif assinatura.status_assinatura == 'canceled':
                print(f"Assinatura {assinatura.id} cancelada. Revogar acesso.")
                assinatura.revogar_acesso()
        except Assinatura.DoesNotExist:
            print(f"ERRO WEBHOOK: Assinatura local com ID {subscription.id} não encontrada.")
            return JsonResponse({'status': 'error', 'message': 'Subscription not found'}, status=400)
        except Exception as e:
            print(f"ERRO WEBHOOK inesperado ao processar customer.subscription.updated: {e}")
            print(f"Detalhes do erro 'e': {str(e)}") # Adicionado para depuração
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


    # Evento: Pagamento de fatura bem-sucedido (renovações e primeira cobrança após trial)
    # Este evento confirma um pagamento efetivo para uma fatura de assinatura.
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        print(f"Webhook: Invoice Payment Succeeded - Invoice ID: {invoice.id}")

        # Processa apenas se a fatura estiver associada a uma assinatura.
        if hasattr(invoice, 'subscription') and invoice.subscription:
            try:
                # Tenta encontrar a assinatura local.
                assinatura = Assinatura.objects.get(stripe_subscription_id=invoice.subscription)
                # Registra o sucesso do pagamento.
                assinatura.registrar_pagamento_sucesso(payment_intent_id=invoice.payment_intent)
                
                # --- CORREÇÃO FINAL PARA DATAS (current_period_start, trial_end, etc.) ---
                # Garante que os valores de timestamp não são None antes da conversão.
                current_period_start_dt = datetime.fromtimestamp(invoice.period_start, tz=timezone.utc) if invoice.period_start else None
                current_period_end_dt = datetime.fromtimestamp(invoice.period_end, tz=timezone.utc) if invoice.period_end else None

                # Atualiza o status e as datas, marcando como ativa.
                assinatura.set_status_and_dates(
                    status='active',
                    current_period_start=current_period_start_dt,
                    current_period_end=current_period_end_dt,
                    trial_end=None # Não está mais em trial se uma fatura foi paga
                )
                assinatura.conceder_acesso()
                print(f"Assinatura {assinatura.id} teve fatura paga com sucesso. Acesso mantido.")
            except Assinatura.DoesNotExist:
                print(f"ERRO WEBHOOK: Assinatura local com ID {invoice.subscription} não encontrada para fatura.")
                return JsonResponse({'status': 'error', 'message': 'Subscription not found for invoice'}, status=400)
            except Exception as e:
                print(f"ERRO WEBHOOK inesperado ao processar invoice.payment_succeeded: {e}")
                print(f"Detalhes do erro 'e': {str(e)}") # Adicionado para depuração
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        else:
            print(f"Webhook: Invoice Payment Succeeded ignorado (não é de assinatura ou subscription ID ausente). Invoice ID: {invoice.id}")
            return JsonResponse({'status': 'success', 'message': 'Invoice not related to subscription or subscription ID missing.'})


    # Evento: Assinatura cancelada
    # Disparado quando uma assinatura é cancelada (pelo cliente, dashboard, ou API).
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        print(f"Webhook: Subscription Deleted - ID: {subscription.id}")
        try:
            assinatura = Assinatura.objects.get(stripe_subscription_id=subscription.id)
            assinatura.registrar_cancelamento()
            print(f"Assinatura {assinatura.id} cancelada e acesso revogado.")
        except Assinatura.DoesNotExist:
            print(f"ERRO WEBHOOK: Assinatura local com ID {subscription.id} não encontrada para deleção.")
            return JsonResponse({'status': 'error', 'message': 'Subscription not found for deletion'}, status=400)
        except Exception as e:
            print(f"ERRO WEBHOOK inesperado ao processar customer.subscription.deleted: {e}")
            print(f"Detalhes do erro 'e': {str(e)}") # Adicionado para depuração
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # Retorna 200 OK para o Stripe indicando que o evento foi recebido e processado.
    # Mesmo que a lógica interna tenha retornado 400/500, este é o último retorno do webhook.
    return JsonResponse({'status': 'success'})


def checkout_page(request, plano_pk):
    plano = get_object_or_404(Plano, pk=plano_pk)
    context = {
        'plano': plano,
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY
    }
    return render(request, 'payments/checkout.html', context)