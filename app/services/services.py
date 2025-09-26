<<<<<<< HEAD
from app.db.db_simulado import usuarios
from fastapi import HTTPException, status

# ---------- Autenticação simples ---------- #
def get_current_user(user_id: int = 2):
    """
    Simula autenticação. Sempre retorna usuário de id=2 (João).
    Em produção, isso viria de JWT/OAuth2.
    """
    user = next((u for u in usuarios if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user

def admin_required(current_user):
    if not current_user["is_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: somente administradores"
        )
    return current_user

# ---------- Função de envio de e-mail ---------- #
def enviar_email(destinatario: str, assunto: str, mensagem: str):
    """
    Aqui poderia integrar com smtplib.
    Por enquanto só simula.
    """
    print(f"📧 Enviando email para {destinatario} | Assunto: {assunto}")
    print("Mensagem:", mensagem)
=======
# Arquivo de índice para importações centralizadas
from .UsuarioService import UsuarioService

# Aqui você pode adicionar outros services conforme necessário
# from .BoletimService import BoletimService
# from .MensagemService import MensagemService

__all__ = [
    "UsuarioService",
    # "BoletimService",
    # "MensagemService",
]
>>>>>>> ba3dfbf8458a298dbf77ecfa373e0ff6fcbcb2e1
