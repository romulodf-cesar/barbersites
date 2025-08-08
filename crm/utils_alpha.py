# crm/utils_alpha.py

import random
import string
import requests
import json
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist # Importado para manter a compatibilidade

# Define o conjunto de caracteres especiais permitidos
ALLOWED_SPECIAL_CHARS = ',.!?@#$%&*-_=+/-'

def generate_random_password(length=12):
    """
    Gera uma senha aleatória forte com o comprimento especificado.
    """
    if length < 4:
        raise ValueError("O comprimento da senha deve ser de pelo menos 4 caracteres.")

    all_chars = string.ascii_letters + string.digits + ALLOWED_SPECIAL_CHARS

    password_chars = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice(ALLOWED_SPECIAL_CHARS)
    ]

    for _ in range(length - len(password_chars)):
        password_chars.append(random.choice(all_chars))

    random.shuffle(password_chars)
    return "".join(password_chars)

def provisionar_admin_em_instancia_mock(instancia_url, api_key, username, email, password, stripe_subscription_id):
    """
    Envia as informações do novo admin para a API da instância mock.
    Esta função é uma adaptação para a versão de apresentação.
    """
    url = f"{instancia_url}/external/admin-users/"
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json',
    }
    body = {
        "username": username,
        "email": email,
        "password": password,
        "stripe_subscription_id": stripe_subscription_id
    }

    try:
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 201:
            print(f"DEBUG: Admin {username} provisionado com sucesso na instância mock em {instancia_url}.")
            return True
        else:
            print(f"ERRO: Falha ao provisionar admin na instância mock. Status: {response.status_code}, Resposta: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"ERRO: Falha na requisição para a instância mock: {e}")
        return False