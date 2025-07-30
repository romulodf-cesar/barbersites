# payments/views.py

# Importações necessárias
import stripe # Biblioteca oficial do Stripe para Python.
import json # Para trabalhar com dados JSON (usado para requisições do frontend).
from django.conf import settings # Para acessar configurações do seu settings.py (como chaves da API do Stripe).
from django.shortcuts import render, get_object_or_404, redirect # Funções utilitárias do Django para renderizar templates, buscar objetos ou redirecionar.
from django.http import JsonResponse, HttpResponse # Para retornar respostas HTTP em formato JSON ou status simples.
from django.views.decorators.csrf import csrf_exempt # Decorador para desativar a proteção CSRF em views específicas (webhooks, AJAX).
from django.urls import reverse # Para gerar URLs dinamicamente com base nos nomes das rotas.

# IMPORTANTE: Importa os modelos do app 'crm', pois são eles que guardam os dados de Plano, Usuário, Barbearia e Assinatura.
from crm.models import Plano, Usuario, Barbearia, Assinatura
# NOVO: Importa os formulários Django que criamos para Usuario e Barbearia (do app crm).
from crm.forms import UsuarioForm, BarbeariaForm 

from datetime import datetime, timezone # Módulo para trabalhar com datas e fusos horários (necessário para timestamps do Stripe).

# Configura a chave secreta do Stripe.
# Esta chave autentica suas requisições para a API do Stripe no backend.
# A chave é lida de settings.STRIPE_SECRET_KEY, que por sua vez, é configurada em seu arquivo .env.
stripe.api_key = settings.STRIPE_SECRET_KEY

# ----------------------------------------------------------------------
# 1. View para exibir a lista de planos na página inicial
#    (Pode ser sua landing page ou uma página dedicada aos planos)
# ----------------------------------------------------------------------
def list_plans(request):
    """
    Lista todos os planos disponíveis do seu modelo 'Plano' (do app crm)
    e os exibe em um template HTML. Esta view serve como o ponto de entrada
    para o usuário escolher um plano para assinar.
    """
    # Busca todos os objetos Plano no banco de dados.
    # Ordena os planos pelo valor para uma exibição organizada no frontend.
    planos = Plano.objects.all().order_by('valor')
    
    # Prepara o dicionário de contexto que será passado para o template HTML.
    context = {
        'planos': planos, # A lista de objetos 'Plano' para o loop no HTML (por exemplo, para renderizar cartões de plano).
        # A chave pública do Stripe (Publishable key) é passada para o frontend.
        # Esta chave é segura para ser exposta publicamente e é utilizada pela biblioteca Stripe.js
        # no navegador do cliente para interagir com a interface de pagamento do Stripe.
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY
    }
    # Renderiza o template 'payments/list_plans.html' com os dados fornecidos no contexto.
    # Este template deve estar localizado em 'sua_pasta_do_projeto/templates/payments/'.
    return render(request, 'payments/list_plans.html', context)

# ----------------------------------------------------------------------
# 2. View para criar uma sessão de checkout no Stripe
#    Esta view é chamada pelo JavaScript do frontend (do checkout.html)
#    quando o usuário preenche o formulário e clica em "Pagar".
# ----------------------------------------------------------------------
# @csrf_exempt 
def create_checkout_session(request, plano_pk):
    plano = get_object_or_404(Plano, pk=plano_pk)

    if request.method == 'POST':
        if not plano.stripe_price_id:
            return JsonResponse({'error': 'Este plano não tem um ID de preço configurado no Stripe.'}, status=400)

        # Processamento de dados via JSON (o frontend envia assim).
        # Agora, vamos VALIDAR esses dados usando Django Forms.
        try:
            data = json.loads(request.body)
            usuario_data = data.get('usuario_data')
            barbearia_data = data.get('barbearia_data')

            # --- NOVO: VALIDAÇÃO DOS DADOS JSON COM DJANGO FORMS ---
            # Instancia os formulários Django com os dados JSON recebidos.
            # 'data' é usado para dados não-POST (como JSON) ao invés de 'request.POST'.
            usuario_form_validation = UsuarioForm(data=usuario_data)
            barbearia_form_validation = BarbeariaForm(data=barbearia_data)

            # Verifica se os dados são válidos de acordo com as regras do formulário/modelo.
            if usuario_form_validation.is_valid() and barbearia_form_validation.is_valid():
                # Se válidos, os dados "limpos" (já convertidos e validados) são acessados via .cleaned_data.
                usuario_cleaned_data = usuario_form_validation.cleaned_data
                barbearia_cleaned_data = barbearia_form_validation.cleaned_data
                print("DEBUG: Dados do formulário Django (via JSON) validados com sucesso!")

                # A partir daqui, usaremos 'usuario_cleaned_data' e 'barbearia_cleaned_data'
                # no lugar de 'usuario_data' e 'barbearia_data' nas etapas seguintes.

            else:
                # Se a validação falhar, inspeciona os erros e retorna para o frontend.
                errors = {
                    'usuario_errors': usuario_form_validation.errors.as_json() if usuario_form_validation.errors else None,
                    'barbearia_errors': barbearia_form_validation.errors.as_json() if barbearia_form_validation.errors else None
                }
                print(f"ERRO DE VALIDAÇÃO DJANGO FORMS: {errors}")
                return JsonResponse({'error': 'Dados do formulário inválidos.', 'details': errors}, status=400)
            # --- FIM DA VALIDAÇÃO DJANGO FORMS ---

            # As variáveis 'usuario_data' e 'barbearia_data' agora são substituídas
            # por 'usuario_cleaned_data' e 'barbearia_cleaned_data'.
            # O restante do código segue como antes, mas com dados validados.

            # 1. Processar/Salvar/Obter Usuário:
            usuario, created_user = Usuario.objects.get_or_create(
                email=usuario_cleaned_data['email'], # Usando dados validados
                defaults={
                    'nome_completo': usuario_cleaned_data['nome_completo'],
                    'telefone': usuario_cleaned_data['telefone'],
                    'aceite_termos': usuario_cleaned_data.get('aceite_termos', False),
                    'receber_notificacoes': usuario_cleaned_data.get('receber_notificacoes', False)
                }
            )
            
            # 2. Processar/Salvar/Obter Barbearia:
            barbearia, created_barber = Barbearia.objects.get_or_create(
                nome_barbearia=barbearia_cleaned_data['nome_barbearia'], # Usando dados validados
                defaults={
                    'endereco': barbearia_cleaned_data['endereco'],
                    'cidade': barbearia_cleaned_data['cidade'],
                    'estado': barbearia_cleaned_data['estado'],
                    'cep': barbearia_cleaned_data['cep']
                }
            )
            
            customer_stripe_id = usuario.stripe_customer_id

            session_params = {
                'line_items': [
                    {
                        'price': plano.stripe_price_id,
                        'quantity': 1,
                    },
                ],
                'mode': 'subscription',
                'success_url': request.build_absolute_uri(reverse('payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
                'cancel_url': request.build_absolute_uri(reverse('payment_cancel')),
            }

            if customer_stripe_id:
                session_params['customer'] = customer_stripe_id
            else:
                session_params['customer_email'] = usuario.email

            if plano.trial_period_days > 0:
                session_params['subscription_data'] = {
                    'trial_period_days': plano.trial_period_days,
                }
                print(f"Criando sessão de assinatura para o plano '{plano.nome_plano}' com {plano.trial_period_days} dias de teste gratuito.")

            checkout_session = stripe.checkout.Session.create(**session_params)

            return JsonResponse({'id': checkout_session.id})
        
        except Exception as e:
            print(f"ERRO ao criar sessão de checkout: {e}")
            return JsonResponse({'error': str(e)}, status=400)


# ----------------------------------------------------------------------
# 3. View para a página de sucesso após o pagamento/assinatura
# ----------------------------------------------------------------------
def payment_success(request):
    """
    Exibe uma página de sucesso para o usuário após ele concluir o checkout no Stripe.
    Recebe o 'session_id' via parâmetro GET na URL (adicionado pelo Stripe após o checkout).
    """
    session_id = request.GET.get('session_id') # Pega o ID da sessão de checkout da URL.
    session = None
    # Se um 'session_id' foi fornecido na URL, tenta recuperar os detalhes da sessão do Stripe.
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id) # Recupera a sessão do Stripe.
        # Captura erros específicos da API do Stripe, caso a sessão não possa ser encontrada.
        except stripe.error.StripeError as e:
            # Se houver erro ao recuperar, renderiza uma página de erro com a mensagem.
            return render(request, 'payments/error.html', {'message': f"Erro ao recuperar sessão: {e}"})
    # Renderiza a página de sucesso, passando os detalhes da sessão (se recuperada).
    # O template deve estar em 'sua_pasta_do_projeto/templates/payments/success.html'.
    return render(request, 'payments/success.html', {'session': session})

# ----------------------------------------------------------------------
# 4. View para a página de cancelamento do pagamento/assinatura
# ----------------------------------------------------------------------
def payment_cancel(request):
    """
    Exibe uma página de cancelamento se o usuário não concluir o checkout no Stripe
    ou se a sessão de checkout for cancelada.
    """
    # Renderiza a página de cancelamento.
    # O template deve estar em 'sua_pasta_do_projeto/templates/payments/cancel.html'.
    return render(request, 'payments/cancel.html')

# ----------------------------------------------------------------------
# 5. View para o Webhook do Stripe (MUITO IMPORTANTE para confirmar pagamentos/assinaturas)
# ----------------------------------------------------------------------
@csrf_exempt # Decorador que desativa a proteção CSRF. É essencial para webhooks porque
             # as requisições vêm diretamente dos servidores do Stripe (ou do Stripe CLI em teste)
             # e não de um navegador com o token CSRF do seu site.
             # A segurança da requisição de webhook é garantida pela verificação da assinatura do Stripe.
def stripe_webhook(request):
    """
    Processa eventos de webhook enviados pelo Stripe.
    Esta é a view mais crítica para a lógica de negócio, pois é aqui que as atualizações
    no seu banco de dados local são realizadas com base no status real dos pagamentos/assinaturas
    no Stripe.
    """
    print("Webhook chamado") # Print para indicar que a view do webhook foi acessada.
    payload = request.body # O corpo da requisição HTTP (contém os dados do evento Stripe em JSON).
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE') # O cabeçalho 'Stripe-Signature', usado para verificar a autenticidade.

    # Tenta construir o objeto 'Event' do Stripe, que representa o evento recebido.
    # Este passo é crucial, pois ele também verifica a autenticidade da requisição usando a chave secreta.
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET # STRIPE_WEBHOOK_SECRET vem do .env.
        )
        print(f"Evento recebido: {event['type']}") # Loga o tipo de evento recebido (ex: 'checkout.session.completed').
    # Captura erros de payload inválido (corpo da requisição mal-formado).
    except ValueError as e:
        print(f"Erro no Webhook: Payload inválido: {e}")
        return HttpResponse(status=400) # Retorna 400 Bad Request (requisição inválida).
    # Captura erros de assinatura inválida.
    # Isso pode acontecer se a chave secreta no seu .env estiver errada,
    # ou se a requisição não veio do Stripe (tentativa de fraude).
    except stripe.error.SignatureVerificationError as e:
        print(f"Erro no Webhook: Assinatura inválida: {e}")
        return HttpResponse(status=400) # Retorna 400 Bad Request.
    # Captura quaisquer outras exceções inesperadas durante a construção do evento.
    except Exception as e:
        print(f"Erro inesperado na construção do evento webhook: {e}")
        return HttpResponse(status=400) # Retorna 400 Bad Request.


    # ------------------------------------------------------------------
    # Lógica de Negócios Baseada no Tipo de Evento
    # ------------------------------------------------------------------

    # Evento: 'checkout.session.completed'
    # Disparado quando o cliente finaliza com sucesso o processo de checkout no Stripe.
    # Este é o principal evento para registrar novas assinaturas ou pagamentos únicos.
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object'] # O objeto 'session' contém todos os detalhes da sessão concluída.
        print(f"Webhook: Checkout Session Completed - Session ID: {session.id}")

        # Verifica se a sessão é para uma assinatura (neste guia, todos os planos são assinaturas).
        if session.mode == 'subscription':
            subscription_id = session.subscription # O ID da Assinatura criada no Stripe.
            customer_id = session.customer # O ID do Cliente no Stripe.
            customer_email = session.customer_details.email if session.customer_details and session.customer_details.email else None
            customer_name = session.customer_details.name if session.customer_details and session.customer_details.name else None

            stripe_price_id = None
            try:
                # --- OBTENDO O stripe_price_id DE FORMA ROBUSTA ---
                # Para sessões de assinatura, o Stripe não garante que 'session.line_items' virá completo
                # no payload do webhook. A forma mais confiável é usar stripe.checkout.Session.list_line_items().
                line_items_from_session = stripe.checkout.Session.list_line_items(session.id)
                
                if line_items_from_session and line_items_from_session.data:
                    first_item = line_items_from_session.data[0] # Pega o primeiro item de linha (assumimos 1 plano por assinatura).
                    if hasattr(first_item, 'price') and first_item.price: # Verifica se o item tem o atributo 'price'.
                        stripe_price_id = first_item.price.id # Extrai o ID do preço do Stripe.
                    else:
                        print(f"ERRO DEBUG: Item de linha da sessão {session.id} não possui atributo 'price'.")
                        # Se não tem price no item, tentar o objeto subscription completo como fallback
                        # Nota: Em alguns casos, Stripe CLI / Stripe API pode não preencher todos os dados imediatamente.
                        stripe_subscription_obj_full = stripe.Subscription.retrieve(subscription_id)
                        if hasattr(stripe_subscription_obj_full, 'items') and \
                           hasattr(stripe_subscription_obj_full.items, 'data') and \
                           stripe_subscription_obj_full.items.data:
                            first_sub_item = stripe_subscription_obj_full.items.data[0]
                            if hasattr(first_sub_item, 'price') and first_sub_item.price:
                                stripe_price_id = first_sub_item.price.id
                            else:
                                raise Exception("Price attribute missing from subscription item (fallback).")
                        else:
                            raise Exception(f"No line items found from subscription or session list (fallback for session {session.id}).")
                else:
                    print(f"ERRO DEBUG: Nenhum item de linha encontrado para sessão {session.id} via list_line_items.")
                    # Tenta o objeto subscription completo como fallback se list_line_items falhou
                    stripe_subscription_obj_full = stripe.Subscription.retrieve(subscription_id)
                    if hasattr(stripe_subscription_obj_full, 'items') and \
                       hasattr(stripe_subscription_obj_full.items, 'data') and \
                       stripe_subscription_obj_full.items.data:
                        first_sub_item = stripe_subscription_obj_full.items.data[0]
                        if hasattr(first_sub_item, 'price') and first_sub_item.price:
                            stripe_price_id = first_sub_item.price.id
                        else:
                            raise Exception("Price attribute missing from subscription item (fallback 2).")
                    else:
                        raise Exception(f"No line items found from subscription or session list (fallback 2 for {subscription_id}).")

            except stripe.error.StripeError as e:
                print(f"ERRO WEBHOOK: Falha ao obter detalhes da assinatura ou line_items para {session.id}: {e}")
                return JsonResponse({'status': 'error', 'message': f"Falha ao obter line_items: {e}"}, status=500)
            except Exception as e:
                print(f"ERRO WEBHOOK INESPERADO ao obter price_id para {session.id}: {e}")
                print(f"Detalhes do erro 'e': {str(e)}") # Adicionado para depuração.
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
            if not stripe_price_id:
                print("ERRO WEBHOOK: stripe_price_id não encontrado na sessão de checkout. Impossível vincular ao plano local.")
                return JsonResponse({'status': 'error', 'message': 'stripe_price_id missing'}, status=400)

            try:
                # 1. Encontrar ou criar o 'Usuario' no seu banco de dados.
                usuario, created_user = Usuario.objects.get_or_create(
                    email=customer_email,
                    defaults={
                        'nome_completo': customer_name if customer_name else customer_email,
                        'telefone': 'N/A'
                    }
                )
                if created_user:
                    print(f"Usuário criado: {usuario.email}")

                # 2. Atualizar o 'stripe_customer_id' do 'Usuario' local, se ele não tiver.
                if not usuario.stripe_customer_id:
                    usuario.stripe_customer_id = customer_id
                    usuario.save()
                    print(f"stripe_customer_id '{customer_id}' associado ao usuário '{usuario.email}'.")

                # 3. Encontrar o 'Plano' correspondente no seu banco de dados.
                plano = Plano.objects.get(stripe_price_id=stripe_price_id)

                # 4. Obter uma 'Barbearia' (assumindo a primeira existente para este cenário).
                barbearia = Barbearia.objects.first()
                if not barbearia:
                    print("AVISO: Nenhuma barbearia encontrada. Não foi possível criar a assinatura localmente.")
                    return JsonResponse({'status': 'success', 'message': 'No barbershop found.'})

                # 5. Criar ou atualizar a 'Assinatura' no seu banco de dados.
                assinatura, created_sub = Assinatura.objects.get_or_create(
                    stripe_subscription_id=subscription_id,
                    defaults={
                        'usuario': usuario,
                        'plano': plano,
                        'barbearia': barbearia,
                        'status_assinatura': 'pendente', # Status temporário
                    }
                )

                if created_sub:
                    print(f"Assinatura localmente criada: {assinatura.id} para {usuario.email}.")
                else:
                    print(f"Assinatura local existente atualizada: {assinatura.id} para {usuario.email}.")

                # 6. Recuperar o objeto de assinatura completo do Stripe para obter o status e as datas precisas.
                stripe_subscription_obj = stripe.Subscription.retrieve(subscription_id)
                print(f"Dados da assinatura do Stripe: {stripe_subscription_obj}") # Imprime o objeto Stripe para depuração.

                # --- CORREÇÃO FINAL PARA DATAS (current_period_start, trial_end, etc.) ---
                # Acessa os atributos de timestamp de forma defensiva usando 'getattr()'.
                # 'getattr(objeto, atributo, valor_padrao)' pega o valor do atributo ou None se não existir.
                current_period_start = getattr(stripe_subscription_obj, 'current_period_start', None)
                current_period_end = getattr(stripe_subscription_obj, 'current_period_end', None)
                trial_end = getattr(stripe_subscription_obj, 'trial_end', None)

                # Converte os timestamps (se existirem e forem válidos) para objetos datetime do Python.
                # Se o valor for None ou 0, a variável resultante será None.
                current_period_start = datetime.fromtimestamp(current_period_start, tz=timezone.utc) if current_period_start else None
                current_period_end = datetime.fromtimestamp(current_period_end, tz=timezone.utc) if current_period_end else None
                trial_end = datetime.fromtimestamp(trial_end, tz=timezone.utc) if trial_end else None

                # 7. Atualizar o status e as datas da assinatura localmente.
                assinatura.set_status_and_dates(
                    status=stripe_subscription_obj.status, # Pega o status real do Stripe (trialing, active, etc.).
                    current_period_start=current_period_start, # Passa o datetime convertido.
                    current_period_end=current_period_end,   # Passa o datetime convertido.
                    trial_end=trial_end # Passa o datetime convertido.
                )
                print(f"Assinatura {assinatura.id} status inicial: {assinatura.status_assinatura}.")
                
                # 8. Conceder ou revogar acesso do usuário com base no status da assinatura.
                if assinatura.status_assinatura == 'trialing' or assinatura.status_assinatura == 'active':
                    assinatura.conceder_acesso() # Chama o método em crm/models.py para conceder acesso.
                else:
                    assinatura.revogar_acesso() # Chama o método para revogar acesso.

            # Captura erro se o Plano do Stripe não for encontrado no seu Django.
            except Plano.DoesNotExist:
                print(f"ERRO WEBHOOK: Plano com stripe_price_id {stripe_price_id} não encontrado localmente.")
                return JsonResponse({'status': 'error', 'message': 'Plano not found'}, status=400)
            # Captura qualquer outra exceção inesperada durante o processamento da assinatura.
            except Exception as e:
                print(f"ERRO WEBHOOK inesperado ao processar criação/atualização da assinatura: {e}")
                print(f"Detalhes do erro 'e': {str(e)}") # Loga os detalhes da exceção para depuração.
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


    # Evento: 'customer.subscription.updated'
    # Disparado quando o status ou os detalhes de uma assinatura mudam (ex: trial termina e vira 'active').
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object'] # Objeto da assinatura do Stripe.
        print(f"Webhook: Subscription Updated - ID: {subscription.id} - Status: {subscription.status}")

        try:
            # Tenta encontrar a assinatura local pelo ID do Stripe.
            assinatura = Assinatura.objects.get(stripe_subscription_id=subscription.id)

            # --- CORREÇÃO FINAL PARA DATAS (current_period_start, trial_end, etc.) ---
            # Acessa os atributos de timestamp de forma defensiva usando 'getattr()'.
            current_period_start = getattr(subscription, 'current_period_start', None)
            current_period_end = getattr(subscription, 'current_period_end', None)
            trial_end = getattr(subscription, 'trial_end', None)

            current_period_start = datetime.fromtimestamp(current_period_start, tz=timezone.utc) if current_period_start else None
            current_period_end = datetime.fromtimestamp(current_period_end, tz=timezone.utc) if current_period_end else None
            trial_end = datetime.fromtimestamp(trial_end, tz=timezone.utc) if trial_end else None

            # Atualiza o status e as datas da assinatura localmente.
            assinatura.set_status_and_dates(
                status=subscription.status,
                current_period_start=current_period_start,
                current_period_end=current_period_end,
                trial_end=trial_end
            )
            print(f"Assinatura {assinatura.id} atualizada com sucesso.")

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
            print(f"Detalhes do erro 'e': {str(e)}") # Adicionado para depuração.
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


    # Evento: 'invoice.payment_succeeded'
    # Disparado quando uma fatura é criada e paga com sucesso.
    # Para assinaturas, isso acontece na primeira cobrança após o término de um trial e em renovações.
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object'] # Objeto da fatura.
        print(f"Webhook: Invoice Payment Succeeded - Invoice ID: {invoice.id}")

        # Processa apenas se a fatura estiver associada a uma assinatura.
        if hasattr(invoice, 'subscription') and invoice.subscription:
            try:
                # Tenta encontrar a assinatura local.
                assinatura = Assinatura.objects.get(stripe_subscription_id=invoice.subscription)
                # Registra o sucesso do pagamento, guardando o ID do PaymentIntent.
                assinatura.registrar_pagamento_sucesso(payment_intent_id=invoice.payment_intent)
                
                # --- CORREÇÃO FINAL PARA DATAS (current_period_start, etc.) ---
                # Acessa os atributos de timestamp de forma defensiva e converte para datetime.
                current_period_start = getattr(invoice, 'period_start', None)
                current_period_end = getattr(invoice, 'period_end', None)

                current_period_start = datetime.fromtimestamp(current_period_start, tz=timezone.utc) if current_period_start else None
                current_period_end = datetime.fromtimestamp(current_period_end, tz=timezone.utc) if current_period_end else None

                # Atualiza o status e as datas, marcando a assinatura como 'active'.
                assinatura.set_status_and_dates(
                    status='active',
                    current_period_start=current_period_start,
                    current_period_end=current_period_end,
                    trial_end=None
                )
                assinatura.conceder_acesso() # Mantém o acesso ativo.
                print(f"Assinatura {assinatura.id} teve fatura paga com sucesso. Acesso mantido.")
            except Assinatura.DoesNotExist:
                print(f"ERRO WEBHOOK: Assinatura local com ID {invoice.subscription} não encontrada para fatura.")
                return JsonResponse({'status': 'error', 'message': 'Subscription not found for invoice'}, status=400)
            except Exception as e:
                print(f"ERRO WEBHOOK inesperado ao processar invoice.payment_succeeded: {e}")
                print(f"Detalhes do erro 'e': {str(e)}") # Adicionado para depuração.
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        else:
            # Se a fatura não está relacionada a uma assinatura, o evento é ignorado (retorna 200 OK).
            print(f"Webhook: Invoice Payment Succeeded ignorado (não é de assinatura ou subscription ID ausente). Invoice ID: {invoice.id}")
            return JsonResponse({'status': 'success', 'message': 'Invoice not related to subscription or subscription ID missing.'})


    # Evento: 'customer.subscription.deleted'
    # Disparado quando uma assinatura é cancelada (pelo cliente no portal, no dashboard do Stripe, ou via API).
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object'] # Objeto da assinatura deletada.
        print(f"Webhook: Subscription Deleted - ID: {subscription.id}")
        try:
            # Tenta encontrar a assinatura local.
            assinatura = Assinatura.objects.get(stripe_subscription_id=subscription.id)
            assinatura.registrar_cancelamento() # Marca a assinatura como cancelada e revoga o acesso.
            print(f"Assinatura {assinatura.id} cancelada e acesso revogado.")
        except Assinatura.DoesNotExist:
            print(f"ERRO WEBHOOK: Assinatura local com ID {subscription.id} não encontrada para deleção.")
            return JsonResponse({'status': 'error', 'message': 'Subscription not found for deletion'}, status=400)
        except Exception as e:
            print(f"ERRO WEBHOOK inesperado ao processar customer.subscription.deleted: {e}")
            print(f"Detalhes do erro 'e': {str(e)}") # Adicionado para depuração.
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # Retorna 200 OK para o Stripe indicando que o evento foi recebido e processado.
    # É fundamental sempre retornar 200 OK para o Stripe, mesmo que a lógica interna
    # tenha retornado um 400/500 (que é capturado pelo nosso try/except principal),
    # para evitar que o Stripe reenvie o mesmo evento repetidamente.
    return JsonResponse({'status': 'success'})



# ----------------------------------------------------------------------
# 6. View para exibir a página de checkout com o formulário de dados do usuário/barbearia
# ----------------------------------------------------------------------
def checkout_page(request, plano_pk):
    """
    Renderiza a página de checkout onde o usuário preenche seus dados
    e os da barbearia antes de iniciar o pagamento.
    """
    # Obtém o plano selecionado pelo seu ID.
    plano = get_object_or_404(Plano, pk=plano_pk)
    
    # NOVO: Instanciar Formulários Django para serem passados ao template.
    # Estes formulários são usados APENAS para renderizar os campos no HTML.
    # A validação real dos dados de POST ocorre em create_checkout_session.
    usuario_form_display = UsuarioForm() 
    barbearia_form_display = BarbeariaForm() 

    context = {
        'plano': plano, 
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY, 
        'usuario_form': usuario_form_display, # Passa a instância do formulário de Usuário.
        'barbearia_form': barbearia_form_display, # Passa a instância do formulário de Barbearia.
    }
    return render(request, 'payments/checkout.html', context)


# # ----------------------------------------------------------------------
# # 6. View para exibir a página de checkout com o formulário de dados do usuário/barbearia
# # ----------------------------------------------------------------------
# def checkout_page(request, plano_pk):
#     """
#     Renderiza a página de checkout onde o usuário preenche seus dados
#     e os da barbearia antes de iniciar o pagamento.
#     """
#     # Obtém o plano selecionado pelo seu ID.
#     plano = get_object_or_404(Plano, pk=plano_pk)
    
#     # ------------------------------------------------------------------
#     # NOVO: Instanciar Formulários Django para serem passados ao template.
#     # Esta é a parte do "híbrido" que permite renderizar os campos do formulário
#     # usando o sistema de templates do Django, mas ainda permitindo a submissão via JS/JSON.
#     # ------------------------------------------------------------------
#     usuario_form_display = UsuarioForm() # Instancia um formulário de usuário vazio.
#     barbearia_form_display = BarbeariaForm() # Instancia um formulário de barbearia vazio.

#     context = {
#         'plano': plano, # O objeto 'Plano' é passado para o template para exibir seus detalhes.
#         'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY, # Chave pública para o Stripe.js no frontend.
#         'usuario_form': usuario_form_display, # O formulário Django para o usuário.
#         'barbearia_form': barbearia_form_display, # O formulário Django para a barbearia.
#     }
#     # Renderiza o template 'payments/checkout.html'.
#     # O template deve estar em 'sua_pasta_do_projeto/templates/payments/checkout.html'.
#     return render(request, 'payments/checkout.html', context)




# # payments/views.py

# # Importações necessárias
# import stripe # Biblioteca oficial do Stripe para Python
# import json # Para trabalhar com dados JSON (recebidos do frontend)
# from django.conf import settings # Para acessar configurações do seu settings.py (chaves do Stripe)
# from django.shortcuts import render, get_object_or_404, redirect # Funções utilitárias do Django
# from django.http import JsonResponse, HttpResponse # Para retornar respostas HTTP e JSON
# from django.views.decorators.csrf import csrf_exempt # Decorador para desativar proteção CSRF em views específicas
# from django.urls import reverse # Para gerar URLs dinamicamente
# # IMPORTANTE: Importa os modelos do app 'crm', pois são eles que guardam os dados de Plano, Usuário, Barbearia e Assinatura
# from crm.models import Plano, Usuario, Barbearia, Assinatura
# from datetime import datetime, timezone # Para trabalhar com datas e fusos horários (necessário para timestamps do Stripe)

# # Configura a chave secreta do Stripe.
# # Essa chave autentica suas requisições para a API do Stripe no backend.
# # settings.STRIPE_SECRET_KEY é lido do seu arquivo .env via settings.py.
# stripe.api_key = settings.STRIPE_SECRET_KEY

# # ----------------------------------------------------------------------
# # 1. View para exibir a lista de planos na página inicial
# # ----------------------------------------------------------------------
# def list_plans(request):
#     """
#     Lista todos os planos disponíveis do seu modelo 'Plano' (do app crm)
#     e os exibe em um template HTML.
#     """
#     # Busca todos os objetos Plano no banco de dados e os ordena pelo valor.
#     # A ordenação por valor é útil para exibir planos do mais barato para o mais caro.
#     planos = Plano.objects.all().order_by('valor')
    
#     # Prepara o contexto que será passado para o template HTML.
#     context = {
#         'planos': planos, # A lista de objetos Plano para o loop no HTML (por exemplo, na index.html ou list_plans.html)
#         # A chave pública do Stripe é passada para o frontend. Ela é segura para ser exposta
#         # e é usada pela biblioteca Stripe.js no navegador do cliente para interagir com o Stripe.
#         'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY
#     }
#     # Renderiza o template 'payments/list_plans.html' com os dados do contexto.
#     # Este template deve estar na pasta 'sua_pasta_do_projeto/templates/payments/'.
#     return render(request, 'payments/list_plans.html', context)

# # ----------------------------------------------------------------------
# # 2. View para criar uma sessão de checkout no Stripe
# #    Esta view é chamada pelo JavaScript do frontend (do checkout.html)
# #    quando o usuário preenche o formulário e clica em "Pagar".
# # ----------------------------------------------------------------------
# @csrf_exempt    # Decorador que desativa a proteção CSRF (Cross-Site Request Forgery) para esta view.
#                 # Isso é necessário porque a requisição POST é feita via JavaScript (Fetch API)
#                 # e não por um formulário Django padrão que inclui o token CSRF automaticamente.
#                 # A segurança é gerenciada manualmente no JavaScript do template, que envia o token.
# def create_checkout_session(request, plano_pk):
#     """
#     Cria uma sessão de checkout no Stripe para um plano de assinatura específico.
#     Recebe o ID do plano (plano_pk) via URL e dados do usuário/barbearia do corpo JSON da requisição.
#     """
#     # Tenta obter o objeto 'Plano' do banco de dados usando o ID (Primary Key) recebido na URL.
#     # Se o plano não for encontrado, Django retorna um erro HTTP 404 (Not Found).
#     plano = get_object_or_404(Plano, pk=plano_pk)

#     # A view processa apenas requisições HTTP POST, pois os dados do formulário
#     # são enviados via POST do frontend.
#     if request.method == 'POST':
#         # Verifica se o 'Plano' local tem um 'stripe_price_id' configurado.
#         # Este ID é crucial para o Stripe saber qual plano cobrar.
#         if not plano.stripe_price_id:
#             # Se o ID não estiver configurado, retorna uma resposta JSON com erro 400 (Bad Request).
#             return JsonResponse({'error': 'Este plano não tem um ID de preço configurado no Stripe.'}, status=400)

#         try:
#             # NOVO: Parseia os dados JSON que foram enviados no corpo da requisição POST.
#             # Estes dados contêm as informações preenchidas pelo usuário no formulário de checkout.
#             data = json.loads(request.body)
#             usuario_data = data.get('usuario_data') # Dados do usuário
#             barbearia_data = data.get('barbearia_data') # Dados da barbearia

#             # Validação básica para garantir que ambos os conjuntos de dados foram recebidos.
#             if not usuario_data or not barbearia_data:
#                 return JsonResponse({'error': 'Dados de usuário ou barbearia ausentes.'}, status=400)

#             # 1. Processar/Salvar/Obter Usuário:
#             # Tenta encontrar um 'Usuario' existente no seu banco de dados pelo 'email'.
#             # Se um usuário com esse email não for encontrado, um novo objeto 'Usuario' é criado.
#             usuario, created_user = Usuario.objects.get_or_create(
#                 email=usuario_data['email'],
#                 defaults={ # Estes são os valores padrão usados se um novo 'Usuario' for criado.
#                     'nome_completo': usuario_data['nome_completo'],
#                     'telefone': usuario_data['telefone'],
#                     'aceite_termos': usuario_data.get('aceite_termos', False), # Usa .get() para pegar o valor ou False se não existir
#                     'receber_notificacoes': usuario_data.get('receber_notificacoes', False)
#                 }
#             )
#             # Observação: Se o usuário já existia (created_user é False), você pode adicionar
#             # lógica aqui para atualizar outros campos do usuário se os dados forem diferentes.
            
#             # 2. Processar/Salvar/Obter Barbearia:
#             # Tenta encontrar uma 'Barbearia' existente pelo 'nome_barbearia'. Se não existir, uma nova é criada.
#             barbearia, created_barber = Barbearia.objects.get_or_create(
#                 nome_barbearia=barbearia_data['nome_barbearia'],
#                 defaults={ # Valores padrão se uma nova 'Barbearia' for criada.
#                     'endereco': barbearia_data['endereco'],
#                     'cidade': barbearia_data['cidade'],
#                     'estado': barbearia_data['estado'],
#                     'cep': barbearia_data['cep']
#                 }
#             )
#             # Observação: Lógica de atualização similar à do 'Usuario' pode ser aplicada aqui.
            
#             # Pega o 'stripe_customer_id' associado ao 'Usuario' local, se já existir.
#             # Este ID é usado para vincular o cliente do seu sistema a um cliente no Stripe,
#             # evitando a criação de múltiplos clientes no Stripe para o mesmo usuário.
#             customer_stripe_id = usuario.stripe_customer_id

#             # Prepara os parâmetros para criar a sessão de checkout no Stripe.
#             session_params = {
#                 'line_items': [ # Define os itens que serão mostrados e cobrados no Stripe Checkout.
#                     {
#                         'price': plano.stripe_price_id, # ID do Preço (Plano) configurado no Stripe Dashboard.
#                         'quantity': 1, # Quantidade do item (neste caso, uma assinatura).
#                     },
#                 ],
#                 'mode': 'subscription', # Define o modo da sessão como 'assinatura' (pagamento recorrente).
#                 # URLs para onde o usuário será redirecionado após a conclusão ou cancelamento no Stripe.
#                 'success_url': request.build_absolute_uri(reverse('payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
#                 'cancel_url': request.build_absolute_uri(reverse('payment_cancel')),
#             }

#             # Lógica para passar o cliente para o Stripe:
#             # Se já temos um 'customer_stripe_id' para este 'Usuario' (de uma compra anterior),
#             # passamos esse ID para o Stripe.
#             if customer_stripe_id:
#                 session_params['customer'] = customer_stripe_id
#             # Caso contrário (se for a primeira compra desse usuário), passamos apenas o e-mail.
#             # O Stripe tentará encontrar um cliente existente com esse e-mail ou criará um novo.
#             else:
#                 session_params['customer_email'] = usuario.email

#             # Adiciona o período de teste gratuito se o plano tiver dias configurados (maior que 0).
#             if plano.trial_period_days > 0:
#                 session_params['subscription_data'] = {
#                     'trial_period_days': plano.trial_period_days,
#                 }
#                 print(f"Criando sessão de assinatura para o plano '{plano.nome_plano}' com {plano.trial_period_days} dias de teste gratuito.")

#             # Cria a sessão de checkout no Stripe.
#             # Esta chamada é uma comunicação direta com a API do Stripe.
#             # A resposta contém o 'id' da sessão de checkout, que será usado pelo JavaScript do frontend.
#             checkout_session = stripe.checkout.Session.create(**session_params)

#             # Retorna o ID da sessão de checkout para o frontend em formato JSON.
#             # O JavaScript do frontend usará este ID para redirecionar o navegador do cliente para a página de checkout do Stripe.
#             return JsonResponse({'id': checkout_session.id})
        
#         # Captura qualquer exceção (erro) que ocorra durante o processo de criação da sessão.
#         except Exception as e:
#             print(f"ERRO ao criar sessão de checkout: {e}") # Loga o erro detalhado no terminal do servidor.
#             return JsonResponse({'error': str(e)}, status=400) # Retorna um erro 400 (Bad Request) ao frontend.

# # ----------------------------------------------------------------------
# # 3. View para a página de sucesso após o pagamento/assinatura
# # ----------------------------------------------------------------------
# def payment_success(request):
#     """
#     Exibe uma página de sucesso para o usuário após ele concluir o checkout no Stripe.
#     Recebe o 'session_id' via parâmetro GET na URL (adicionado pelo Stripe após o checkout).
#     """
#     session_id = request.GET.get('session_id') # Pega o ID da sessão de checkout da URL.
#     session = None
#     # Se um 'session_id' foi fornecido na URL, tenta recuperar os detalhes da sessão do Stripe.
#     if session_id:
#         try:
#             session = stripe.checkout.Session.retrieve(session_id) # Recupera a sessão do Stripe.
#         # Captura erros específicos da API do Stripe, caso a sessão não possa ser encontrada.
#         except stripe.error.StripeError as e:
#             # Se houver erro ao recuperar, renderiza uma página de erro com a mensagem.
#             return render(request, 'payments/error.html', {'message': f"Erro ao recuperar sessão: {e}"})
#     # Renderiza a página de sucesso, passando os detalhes da sessão (se recuperados).
#     # O template deve estar em 'sua_pasta_do_projeto/templates/payments/success.html'.
#     return render(request, 'payments/success.html', {'session': session})

# # ----------------------------------------------------------------------
# # 4. View para a página de cancelamento do pagamento/assinatura
# # ----------------------------------------------------------------------
# def payment_cancel(request):
#     """
#     Exibe uma página de cancelamento se o usuário não concluir o checkout no Stripe
#     ou se a sessão de checkout for cancelada.
#     """
#     # Renderiza a página de cancelamento.
#     # O template deve estar em 'sua_pasta_do_projeto/templates/payments/cancel.html'.
#     return render(request, 'payments/cancel.html')

# # ----------------------------------------------------------------------
# # 5. View para o Webhook do Stripe (MUITO IMPORTANTE para confirmar pagamentos/assinaturas)
# # ----------------------------------------------------------------------
# @csrf_exempt # Decorador que desativa a proteção CSRF. É essencial para webhooks porque
#              # as requisições vêm diretamente dos servidores do Stripe (ou do Stripe CLI em teste)
#              # e não de um navegador com o token CSRF do seu site.
#              # A segurança da requisição de webhook é garantida pela verificação da assinatura do Stripe.
# def stripe_webhook(request):
#     """
#     Processa eventos de webhook enviados pelo Stripe.
#     Esta é a view mais crítica para a lógica de negócio, pois é aqui que as atualizações
#     no seu banco de dados local são realizadas com base no status real dos pagamentos/assinaturas
#     no Stripe.
#     """
#     print("Webhook chamado") # Print para indicar que a view do webhook foi acessada.
#     payload = request.body # O corpo da requisição HTTP (contém os dados do evento Stripe em JSON).
#     sig_header = request.META.get('HTTP_STRIPE_SIGNATURE') # O cabeçalho 'Stripe-Signature', usado para verificar a autenticidade.

#     # Tenta construir o objeto 'Event' do Stripe, que representa o evento recebido.
#     # Este passo é crucial, pois ele também verifica a autenticidade da requisição usando a chave secreta.
#     try:
#         event = stripe.Webhook.construct_event(
#             payload, sig_header, settings.STRIPE_WEBHOOK_SECRET # STRIPE_WEBHOOK_SECRET vem do .env.
#         )
#         print(f"Evento recebido: {event['type']}") # Loga o tipo de evento recebido (ex: 'checkout.session.completed').
#     # Captura erros se o payload (corpo da requisição) estiver mal-formado.
#     except ValueError as e:
#         print(f"Erro no Webhook: Payload inválido: {e}")
#         return HttpResponse(status=400) # Retorna um 400 Bad Request (requisição inválida).
#     # Captura erros se a assinatura do webhook for inválida.
#     # Isso pode acontecer se a chave secreta no seu .env estiver errada,
#     # ou se a requisição não veio do Stripe (tentativa de fraude).
#     except stripe.error.SignatureVerificationError as e:
#         print(f"Erro no Webhook: Assinatura inválida: {e}")
#         return HttpResponse(status=400) # Retorna um 400 Bad Request.
#     # Captura quaisquer outras exceções inesperadas durante a construção do evento.
#     except Exception as e:
#         print(f"Erro inesperado na construção do evento webhook: {e}")
#         return HttpResponse(status=400) # Retorna um 400 Bad Request.


#     # ------------------------------------------------------------------
#     # Lógica de Negócios Baseada no Tipo de Evento
#     # ------------------------------------------------------------------

#     # Evento: 'checkout.session.completed'
#     # Disparado quando o cliente finaliza com sucesso o processo de checkout no Stripe.
#     # Este é o principal evento para registrar novas assinaturas ou pagamentos únicos.
#     if event['type'] == 'checkout.session.completed':
#         session = event['data']['object'] # O objeto 'session' contém todos os detalhes da sessão concluída.
#         print(f"Webhook: Checkout Session Completed - Session ID: {session.id}")

#         # Verifica se a sessão é para uma assinatura (neste guia, todos os planos são assinaturas).
#         if session.mode == 'subscription':
#             subscription_id = session.subscription # O ID da Assinatura criada no Stripe.
#             customer_id = session.customer # O ID do Cliente no Stripe.
#             customer_email = session.customer_details.email if session.customer_details else None # E-mail do cliente.
#             customer_name = session.customer_details.name if session.customer_details else None # Nome do cliente.

#             stripe_price_id = None
#             try:
#                 # --- OBTENDO O stripe_price_id DE FORMA ROBUSTA ---
#                 # Para sessões de assinatura, o Stripe não garante que 'session.line_items' virá completo
#                 # no payload do webhook. A forma mais confiável é usar stripe.checkout.Session.list_line_items().
#                 line_items_from_session = stripe.checkout.Session.list_line_items(session.id)
                
#                 # Verifica se a chamada retornou itens e se há dados dentro.
#                 if line_items_from_session and line_items_from_session.data:
#                     first_item = line_items_from_session.data[0] # Pega o primeiro item de linha (assumimos 1 plano por assinatura).
#                     # Verifica se o item de linha tem o atributo 'price' e se não é nulo.
#                     if hasattr(first_item, 'price') and first_item.price:
#                         stripe_price_id = first_item.price.id # Extrai o ID do preço do Stripe.
#                     else:
#                         print(f"ERRO DEBUG: Item de linha da sessão {session.id} não possui atributo 'price'.")
#                         # Se o price_id não foi encontrado, levanta uma exceção para o erro ser capturado.
#                         raise Exception("Price attribute missing from line item after listing.")
#                 else:
#                     print(f"ERRO DEBUG: Nenhum item de linha encontrado para sessão {session.id} via list_line_items.")
#                     # Se a lista de itens da sessão está vazia, levanta uma exceção.
#                     raise Exception("No line items found for checkout session after listing.")

#                 # Se a extração do stripe_price_id falhar, as exceções acima serão capturadas.
            
#             # Captura erros específicos da API do Stripe durante a chamada a list_line_items.
#             except stripe.error.StripeError as e:
#                 print(f"ERRO WEBHOOK: Falha ao obter detalhes da assinatura ou line_items para {session.id}: {e}")
#                 return JsonResponse({'status': 'error', 'message': f"Falha ao obter detalhes da assinatura: {e}"}, status=500)
#             # Captura quaisquer outras exceções inesperadas durante a extração do price_id.
#             except Exception as e:
#                 print(f"ERRO WEBHOOK INESPERADO ao obter price_id para {session.id}: {e}")
#                 print(f"Detalhes do erro 'e': {str(e)}") # Adicionado para depuração
#                 return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
#             # Se, por algum motivo, o stripe_price_id ainda não foi encontrado, retorna 400.
#             if not stripe_price_id:
#                 print("ERRO WEBHOOK: stripe_price_id não encontrado na sessão de checkout. Impossível vincular ao plano local.")
#                 return JsonResponse({'status': 'error', 'message': 'stripe_price_id missing'}, status=400)

#             try:
#                 # 1. Encontrar ou criar o 'Usuario' no seu banco de dados.
#                 usuario, created_user = Usuario.objects.get_or_create(
#                     email=customer_email,
#                     defaults={
#                         'nome_completo': customer_name if customer_name else customer_email,
#                         'telefone': 'N/A' # Telefone pode ser preenchido por um formulário mais completo do Stripe.
#                     }
#                 )
#                 if created_user:
#                     print(f"Usuário criado: {usuario.email}")

#                 # 2. Atualizar o 'stripe_customer_id' do 'Usuario' local, se ele não tiver.
#                 if not usuario.stripe_customer_id:
#                     usuario.stripe_customer_id = customer_id
#                     usuario.save()
#                     print(f"stripe_customer_id '{customer_id}' associado ao usuário '{usuario.email}'.")

#                 # 3. Encontrar o 'Plano' correspondente no seu banco de dados (usando o stripe_price_id).
#                 plano = Plano.objects.get(stripe_price_id=stripe_price_id)

#                 # 4. Obter uma 'Barbearia' (assumindo a primeira barbearia existente para este cenário "coringa").
#                 # Em um cenário real, a 'Barbearia' seria associada de forma mais específica (ex: pelo formulário, ou perfil do usuário).
#                 barbearia = Barbearia.objects.first()
#                 if not barbearia:
#                     print("AVISO: Nenhuma barbearia encontrada. Não foi possível criar a assinatura localmente.")
#                     # Retorna 200 OK para o Stripe, mas com uma mensagem de aviso.
#                     return JsonResponse({'status': 'success', 'message': 'No barbershop found.'}) 

#                 # 5. Criar ou atualizar a 'Assinatura' no seu banco de dados.
#                 # Usamos o 'stripe_subscription_id' como chave principal para garantir unicidade e evitar duplicatas.
#                 assinatura, created_sub = Assinatura.objects.get_or_create(
#                     stripe_subscription_id=subscription_id,
#                     defaults={ # Valores padrão para um novo registro de 'Assinatura'
#                         'usuario': usuario,
#                         'plano': plano,
#                         'barbearia': barbearia,
#                         'status_assinatura': 'pendente', # Status temporário, será atualizado logo em seguida
#                     }
#                 )

#                 if created_sub:
#                     print(f"Assinatura localmente criada: {assinatura.id} para {usuario.email}.")
#                 else:
#                     print(f"Assinatura local existente atualizada: {assinatura.id} para {usuario.email}.")

#                 # 6. Recuperar o objeto de assinatura completo do Stripe para obter o status e as datas precisas.
#                 stripe_subscription_obj = stripe.Subscription.retrieve(subscription_id)
#                 print(f"Dados da assinatura do Stripe: {stripe_subscription_obj}") # Imprime o objeto completo do Stripe para depuração

#                 # --- CORREÇÃO FINAL PARA DATAS (current_period_start, trial_end, etc.) ---
#                 # Acessa os atributos de timestamp de forma defensiva usando 'getattr()'.
#                 # 'getattr(objeto, atributo, valor_padrao)' tenta obter o atributo; se não existir, retorna o valor padrão (None aqui).
#                 current_period_start = getattr(stripe_subscription_obj, 'current_period_start', None)
#                 current_period_end = getattr(stripe_subscription_obj, 'current_period_end', None)
#                 trial_end = getattr(stripe_subscription_obj, 'trial_end', None)

#                 # Converte os timestamps (se existirem e forem válidos) para objetos datetime do Python.
#                 # Se o valor for None ou 0 (que datetime.fromtimestamp não aceita diretamente), a variável será None.
#                 current_period_start = datetime.fromtimestamp(current_period_start, tz=timezone.utc) if current_period_start else None
#                 current_period_end = datetime.fromtimestamp(current_period_end, tz=timezone.utc) if current_period_end else None
#                 trial_end = datetime.fromtimestamp(trial_end, tz=timezone.utc) if trial_end else None

#                 # 7. Atualizar o status e as datas da assinatura localmente usando o método auxiliar.
#                 assinatura.set_status_and_dates(
#                     status=stripe_subscription_obj.status, # Pega o status real do Stripe (trialing, active, etc.)
#                     current_period_start=current_period_start,
#                     current_period_end=current_period_end,
#                     trial_end=trial_end
#                 )
#                 print(f"Assinatura {assinatura.id} status inicial: {assinatura.status_assinatura}.")
                
#                 # 8. Conceder ou revogar acesso do usuário com base no status da assinatura.
#                 if assinatura.status_assinatura == 'trialing' or assinatura.status_assinatura == 'active':
#                     assinatura.conceder_acesso() # Chama o método para conceder acesso (seus prints no models.py)
#                 else:
#                     assinatura.revogar_acesso() # Chama o método para revogar acesso

#             # Captura erro se o 'Plano' do Stripe não for encontrado no seu Django.
#             except Plano.DoesNotExist:
#                 print(f"ERRO WEBHOOK: Plano com stripe_price_id {stripe_price_id} não encontrado localmente.")
#                 return JsonResponse({'status': 'error', 'message': 'Plano not found'}, status=400)
#             # Captura qualquer outra exceção inesperada durante o processamento da assinatura.
#             except Exception as e:
#                 print(f"ERRO WEBHOOK inesperado ao processar criação/atualização da assinatura: {e}")
#                 print(f"Detalhes do erro 'e': {str(e)}") # Loga os detalhes da exceção para depuração
#                 return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


#     # Evento: 'customer.subscription.updated'
#     # Disparado quando o status ou os detalhes de uma assinatura mudam (ex: trial termina e vira 'active').
#     elif event['type'] == 'customer.subscription.updated':
#         subscription = event['data']['object'] # Objeto da assinatura do Stripe
#         print(f"Webhook: Subscription Updated - ID: {subscription.id} - Status: {subscription.status}")

#         try:
#             # Tenta encontrar a assinatura local pelo ID do Stripe.
#             assinatura = Assinatura.objects.get(stripe_subscription_id=subscription.id)

#             # --- CORREÇÃO FINAL PARA DATAS (current_period_start, trial_end, etc.) ---
#             # Acessa os atributos de timestamp de forma defensiva e converte para datetime.
#             current_period_start = getattr(subscription, 'current_period_start', None)
#             current_period_end = getattr(subscription, 'current_period_end', None)
#             trial_end = getattr(subscription, 'trial_end', None)

#             current_period_start = datetime.fromtimestamp(current_period_start, tz=timezone.utc) if current_period_start else None
#             current_period_end = datetime.fromtimestamp(current_period_end, tz=timezone.utc) if current_period_end else None
#             trial_end = datetime.fromtimestamp(trial_end, tz=timezone.utc) if trial_end else None

#             # Atualiza o status e as datas da assinatura localmente.
#             assinatura.set_status_and_dates(
#                 status=subscription.status,
#                 current_period_start=current_period_start,
#                 current_period_end=current_period_end,
#                 trial_end=trial_end
#             )
#             print(f"Assinatura {assinatura.id} atualizada com sucesso.")

#             # Lógica para conceder ou revogar acesso com base no novo status.
#             if assinatura.status_assinatura == 'active':
#                 print(f"Assinatura {assinatura.id} ativada/renovada. Acesso concedido/mantido.")
#                 assinatura.conceder_acesso()
#             elif assinatura.status_assinatura == 'past_due' or subscription.status == 'unpaid': # Verifica se está vencida ou não paga.
#                 print(f"Assinatura {assinatura.id} vencida/não paga. Considerar suspender acesso.")
#                 assinatura.revogar_acesso()
#             elif assinatura.status_assinatura == 'canceled':
#                 print(f"Assinatura {assinatura.id} cancelada. Revogar acesso.")
#                 assinatura.revogar_acesso()
#         except Assinatura.DoesNotExist:
#             print(f"ERRO WEBHOOK: Assinatura local com ID {subscription.id} não encontrada.")
#             return JsonResponse({'status': 'error', 'message': 'Subscription not found'}, status=400)
#         except Exception as e:
#             print(f"ERRO WEBHOOK inesperado ao processar customer.subscription.updated: {e}")
#             print(f"Detalhes do erro 'e': {str(e)}") # Adicionado para depuração
#             return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


#     # Evento: 'invoice.payment_succeeded'
#     # Disparado quando uma fatura é criada e paga com sucesso.
#     # Para assinaturas, isso acontece na primeira cobrança após o término de um trial e em renovações.
#     elif event['type'] == 'invoice.payment_succeeded':
#         invoice = event['data']['object'] # Objeto da fatura
#         print(f"Webhook: Invoice Payment Succeeded - Invoice ID: {invoice.id}")

#         # Processa apenas se a fatura estiver associada a uma assinatura.
#         if hasattr(invoice, 'subscription') and invoice.subscription:
#             try:
#                 # Tenta encontrar a assinatura local.
#                 assinatura = Assinatura.objects.get(stripe_subscription_id=invoice.subscription)
#                 # Registra o sucesso do pagamento, guardando o ID do PaymentIntent.
#                 assinatura.registrar_pagamento_sucesso(payment_intent_id=invoice.payment_intent)
                
#                 # --- CORREÇÃO FINAL PARA DATAS (current_period_start, etc.) ---
#                 # Acessa os atributos de timestamp de forma defensiva e converte para datetime.
#                 current_period_start = getattr(invoice, 'period_start', None)
#                 current_period_end = getattr(invoice, 'period_end', None)

#                 current_period_start = datetime.fromtimestamp(current_period_start, tz=timezone.utc) if current_period_start else None
#                 current_period_end = datetime.fromtimestamp(current_period_end, tz=timezone.utc) if current_period_end else None

#                 # Atualiza o status e as datas, marcando a assinatura como 'active'.
#                 assinatura.set_status_and_dates(
#                     status='active',
#                     current_period_start=current_period_start,
#                     current_period_end=current_period_end,
#                     trial_end=None # A assinatura não está mais em trial se uma fatura foi paga.
#                 )
#                 assinatura.conceder_acesso() # Mantém o acesso ativo.
#                 print(f"Assinatura {assinatura.id} teve fatura paga com sucesso. Acesso mantido.")
#             except Assinatura.DoesNotExist:
#                 print(f"ERRO WEBHOOK: Assinatura local com ID {invoice.subscription} não encontrada para fatura.")
#                 return JsonResponse({'status': 'error', 'message': 'Subscription not found for invoice'}, status=400)
#             except Exception as e:
#                 print(f"ERRO WEBHOOK inesperado ao processar invoice.payment_succeeded: {e}")
#                 print(f"Detalhes do erro 'e': {str(e)}") # Adicionado para depuração
#                 return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
#         else:
#             # Se a fatura não está relacionada a uma assinatura, o evento é ignorado (retorna 200 OK).
#             print(f"Webhook: Invoice Payment Succeeded ignorado (não é de assinatura ou subscription ID ausente). Invoice ID: {invoice.id}")
#             return JsonResponse({'status': 'success', 'message': 'Invoice not related to subscription or subscription ID missing.'})


#     # Evento: 'customer.subscription.deleted'
#     # Disparado quando uma assinatura é cancelada (pelo cliente no portal, no dashboard do Stripe, ou via API).
#     elif event['type'] == 'customer.subscription.deleted':
#         subscription = event['data']['object'] # Objeto da assinatura deletada.
#         print(f"Webhook: Subscription Deleted - ID: {subscription.id}")
#         try:
#             # Tenta encontrar a assinatura local.
#             assinatura = Assinatura.objects.get(stripe_subscription_id=subscription.id)
#             assinatura.registrar_cancelamento() # Marca a assinatura como cancelada e revoga o acesso.
#             print(f"Assinatura {assinatura.id} cancelada e acesso revogado.")
#         except Assinatura.DoesNotExist:
#             print(f"ERRO WEBHOOK: Assinatura local com ID {subscription.id} não encontrada para deleção.")
#             return JsonResponse({'status': 'error', 'message': 'Subscription not found for deletion'}, status=400)
#         except Exception as e:
#             print(f"ERRO WEBHOOK inesperado ao processar customer.subscription.deleted: {e}")
#             print(f"Detalhes do erro 'e': {str(e)}") # Adicionado para depuração
#             return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

#     # Retorna 200 OK para o Stripe indicando que o evento foi recebido e processado.
#     # É fundamental sempre retornar 200 OK para o Stripe, mesmo que a lógica interna
#     # tenha retornado um 400/500 (que é capturado pelo nosso try/except principal),
#     # para evitar que o Stripe reenvie o mesmo evento repetidamente.
#     return JsonResponse({'status': 'success'})


# # ----------------------------------------------------------------------
# # 6. View para exibir a página de checkout com o formulário de dados do usuário/barbearia
# # ----------------------------------------------------------------------
# def checkout_page(request, plano_pk):
#     """
#     Renderiza a página de checkout onde o usuário preenche seus dados
#     e os da barbearia antes de iniciar o pagamento.
#     """
#     # Obtém o plano selecionado pelo seu ID.
#     plano = get_object_or_404(Plano, pk=plano_pk)
#     context = {
#         'plano': plano, # O objeto Plano é passado para o template para exibir seus detalhes.
#         'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY # Chave pública para o Stripe.js no frontend.
#     }
#     # Renderiza o template 'payments/checkout.html'.
#     # O template deve estar em 'sua_pasta_do_projeto/templates/payments/checkout.html'.
#     return render(request, 'payments/checkout.html', context)