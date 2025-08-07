# api/permissions.py
from rest_framework import permissions

class HasAPIKey(permissions.BasePermission):
    """
    Permissão customizada que verifica se a requisição foi autenticada com uma API Key.
    """
    def has_permission(self, request, view):
        # Retorna True se a requisição tem uma chave de autenticação (request.auth)
        # que foi definida pela sua classe de autenticação.
        return request.auth is not None or request.user.is_authenticated