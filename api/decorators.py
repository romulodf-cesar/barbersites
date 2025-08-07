from django.conf import settings
from django.http import JsonResponse
import functools

def api_key_required(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Verifica se a chave de API está presente no cabeçalho 'Authorization'
        # Esperamos o formato: Authorization: Token SUA_CHAVE_SECRETA
        auth_header = request.headers.get('Authorization')

        print(f"DEBUG: Authorization header recebido: '{auth_header}'")

        if not auth_header:
            return JsonResponse({'error': 'Authorization header missing'}, status=401)

        try:
            # Divide o cabeçalho para obter o tipo (Token) e a chave
            token_type, api_key = auth_header.split(' ', 1)
        except ValueError:
            return JsonResponse({'error': 'Invalid Authorization header format'}, status=401)

        if token_type.lower() != 'token':
            return JsonResponse({'error': 'Unsupported authentication type. Use "Token"'}, status=401)

        # Compara a chave fornecida com a chave configurada em settings
        if api_key != settings.CRM_TO_TEMPLATE_API_KEY:
            return JsonResponse({'error': 'Invalid API Key'}, status=403) # 403 Forbidden

        # Se a chave for válida, executa a view original
        return view_func(request, *args, **kwargs)
    return wrapper