from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings

class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')

        if not auth_header:
            return None # Retorna None se não houver cabeçalho, permitindo outras classes de autenticação serem testadas

        try:
            token_type, api_key = auth_header.split(' ', 1)
        except ValueError:
            raise AuthenticationFailed('Invalid Authorization header format. Use "Token <your-key>"')

        if token_type.lower() != 'token':
            raise AuthenticationFailed('Unsupported authentication type. Use "Token"')

        if api_key != settings.CRM_TO_TEMPLATE_API_KEY:
            raise AuthenticationFailed('Invalid API Key')

        # Se a chave for válida, autentica um usuário.
        # Aqui, você pode retornar um usuário, ou None.
        # Para um sistema com API Key, muitas vezes você não tem um "usuário"
        # real associado. Retornar um tuple (None, None) indica sucesso na autenticação,
        # mas sem um objeto de usuário.
        return (None, None)