import os
import secrets
import string
import hashlib
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from db.neon_db import execute_query

class PasswordRecoveryService:
    def __init__(self):
        self.sendgrid_key = os.getenv("SENDGRID_API_KEY")
        self.email_from = os.getenv("EMAIL_FROM")

    def generate_password(self, length: int = 10) -> str:
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def hash_password(self, plain: str) -> str:
        return hashlib.sha256(plain.encode("utf-8")).hexdigest()

    def find_user_by_email(self, email: str):
        rows = execute_query("SELECT id, email FROM usuarios WHERE email = %s LIMIT 1", (email,))
        return rows[0] if rows else None

    def update_user_password(self, user_id: int, hashed: str):
        execute_query("UPDATE usuarios SET senha = %s WHERE id = %s", (hashed, user_id))

    def send_email(self, to_email: str, new_password: str):
        message = Mail(
            from_email=self.email_from,
            to_emails=to_email,
            subject='Recuperação de Senha',
            html_content=f'<p>Sua nova senha temporária é: <strong>{new_password}</strong></p><p>Troque após o login.</p>'
        )
        
        sg = SendGridAPIClient(self.sendgrid_key)
        sg.send(message)

    def recover(self, email: str):
        user = self.find_user_by_email(email)
        if not user:
            return False, "Usuário não encontrado"
        
        new_pass = self.generate_password()
        hashed = self.hash_password(new_pass)
        self.update_user_password(user[0], hashed)
        self.send_email(email, new_pass)
        return True, "Senha redefinida e enviada"