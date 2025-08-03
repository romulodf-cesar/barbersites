import random # Módulo para geração de números aleatórios
import string # Módulo para acessar strings de caracteres (letras, dígitos, pontuação)

# Define o conjunto de caracteres especiais permitidos, conforme sua especificação.
# Não inclui acentuação ou til.
ALLOWED_SPECIAL_CHARS = ',.!?@#$%&*-_=+/-' # Se quiser outros caracteres especiais, adicione aqui.

def senha_chumbada():
    """
    Gera uma senha 'chumbada', que é uma senha fraca e previsível.
    """
    return "Senha123."

def generate_random_password(length=12): # Padrão para 12 caracteres.
    """
    Gera uma senha aleatória forte com o comprimento especificado (padrão 12 caracteres).

    A senha gerada garante que conterá:
    - Pelo menos uma letra minúscula.
    - Pelo menos uma letra maiúscula.
    - Pelo menos um dígito (0-9).
    - Pelo menos um caractere especial do conjunto ALLOWED_SPECIAL_CHARS.

    Args:
        length (int): O comprimento desejado para a senha. Padrão é 12 caracteres.
                      Deve ser pelo menos 4 para garantir todos os tipos de caracteres.

    Returns:
        str: A senha aleatória gerada.
    """
    if length < 4:
        raise ValueError("O comprimento da senha deve ser de pelo menos 4 caracteres para garantir complexidade.")

    # Define os conjuntos de caracteres a serem usados na senha.
    # string.ascii_letters: Todas as letras maiúsculas e minúsculas (a-z, A-Z)
    # string.digits: Todos os dígitos (0-9)
    # ALLOWED_SPECIAL_CHARS: Caracteres especiais definidos por você.
    all_chars = string.ascii_letters + string.digits + ALLOWED_SPECIAL_CHARS

    # Garante que a senha contenha pelo menos um de cada tipo de caractere,
    # para atender aos requisitos de segurança.
    password_chars = [
        random.choice(string.ascii_lowercase), # Uma letra minúscula
        random.choice(string.ascii_uppercase), # Uma letra maiúscula
        random.choice(string.digits),          # Um dígito
        random.choice(ALLOWED_SPECIAL_CHARS)   # Um caractere especial permitido
    ]

    # Preenche o restante da senha com caracteres aleatórios dos conjuntos combinados,
    # até atingir o comprimento desejado.
    for _ in range(length - len(password_chars)):
        password_chars.append(random.choice(all_chars))

    # Embaralha a lista de caracteres da senha para garantir que a ordem seja aleatória
    # e os tipos de caracteres não apareçam sempre no início.
    random.shuffle(password_chars)

    # Junta a lista de caracteres para formar a string final da senha.
    return "".join(password_chars)


def validate_password_strength(password):
    """
    Valida se uma senha atende aos critérios de força especificados:
    - Comprimento entre 8 e 16 caracteres.
    - Contém pelo menos uma letra minúscula.
    - Contém pelo menos uma letra maiúscula.
    - Contém pelo menos um dígito.
    - Contém pelo menos um caractere especial do conjunto ALLOWED_SPECIAL_CHARS.
    - Não contém caracteres não permitidos (incluindo acentuação/til).

    Args:
        password (str): A senha a ser validada.

    Returns:
        bool: True se a senha for forte e válida, False caso contrário.
        list: Uma lista de strings descrevendo os problemas, se houver.
    """
    problems = []

    # 1. Verificar Comprimento
    if not (8 <= len(password) <= 16):
        problems.append("A senha deve ter entre 8 e 16 caracteres.")

    # 2. Verificar Tipos de Caracteres
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in ALLOWED_SPECIAL_CHARS for c in password)

    if not has_lower:
        problems.append("A senha deve conter pelo menos uma letra minúscula.")
    if not has_upper:
        problems.append("A senha deve conter pelo menos uma letra maiúscula.")
    if not has_digit:
        problems.append("A senha deve conter pelo menos um número.")
    if not has_special:
        problems.append(f"A senha deve conter pelo menos um caractere especial permitido: {ALLOWED_SPECIAL_CHARS}")

    # 3. Verificar Caracteres Não Permitidos
    # Todos os caracteres na senha devem estar nos conjuntos permitidos.
    allowed_chars_set = set(string.ascii_letters + string.digits + ALLOWED_SPECIAL_CHARS)
    for char in password:
        if char not in allowed_chars_set:
            problems.append(f"A senha contém um caractere não permitido: '{char}'.")
            break # Não precisa verificar o resto da senha se já achou um inválido.

    if problems:
        return False, problems
    
    return True, []

# Exemplo de uso para teste (você pode rodar este arquivo crm/utils.py diretamente para testar)
# if __name__ == "__main__":
#     print("\n--- Teste de Geração de Senha ---")
#     senha_gerada = generate_random_password()
#     print(f"Senha gerada: {senha_gerada}")
#     is_valid_generated, problems_generated = validate_password_strength(senha_gerada)
#     print(f"É válida? {is_valid_generated}, Problemas: {problems_generated}")

#     print("\n--- Teste de Validação de Senha (Usuário) ---")
#     senha1 = "Senha!234" 
#     is_valid1, problems1 = validate_password_strength(senha1)
#     print(f"'{senha1}' é válida? {is_valid1}, Problemas: {problems1}")

#     senha2 = "senhafraca" 
#     is_valid2, problems2 = validate_password_strength(senha2)
#     print(f"'{senha2}' é válida? {is_valid2}, Problemas: {problems2}")

#     senha3 = "MinhaSenha@123!" 
#     is_valid3, problems3 = validate_password_strength(senha3)
#     print(f"'{senha3}' é válida? {is_valid3}, Problemas: {problems3}")

#     senha4 = "Sa!@#$%" 
#     is_valid4, problems4 = validate_password_strength(senha4)
#     print(f"'{senha4}' é válida? {is_valid4}, Problemas: {problems4}")

#     senha5 = "SenhaComAcentoÁÉ!" 
#     is_valid5, problems5 = validate_password_strength(senha5)
#     print(f"'{senha5}' é válida? {is_valid5}, Problemas: {problems5}")