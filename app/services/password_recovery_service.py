import os
import secrets
import string
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from db.neon_db import NeonDB  # ✅ Use a classe NeonDB
from services.auth_service import get_password_hash

load_dotenv()

class PasswordRecoveryService:
    def __init__(self):
        self.sendgrid_key = os.getenv("SENDGRID_API_KEY")
        self.email_from = os.getenv("EMAIL_FROM")
        self.db = NeonDB()  # ✅ Instancia conexão
        
        if not self.sendgrid_key or not self.email_from:
            raise ValueError("SENDGRID_API_KEY ou EMAIL_FROM não configurados no .env")

    def generate_password(self, length: int = 10) -> str:
        """Gera senha aleatória segura"""
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def find_user_by_email(self, email: str):
        """Busca usuário pelo e-mail na tabela 'usuario'"""
        print(f"🔍 DEBUG: Buscando e-mail: '{email}'")
        print(f"🔍 DEBUG: Tipo do email: {type(email)}")
        
        rows = self.db.fetchall(
            "SELECT id, email FROM usuario WHERE email = %s LIMIT 1", 
            [email]
        )
        
        print(f"🔍 DEBUG: Query retornou: {rows}")
        print(f"🔍 DEBUG: Tipo do retorno: {type(rows)}")
        print(f"🔍 DEBUG: Número de linhas: {len(rows) if rows else 0}")
        
        return rows[0] if rows else None

    def update_user_password(self, user_id: int, hashed: str):
        """Atualiza senha do usuário no banco"""
        self.db.execute(
            "UPDATE usuario SET senha = %s WHERE id = %s", 
            [hashed, user_id]
        )
        self.db.commit()  # ✅ Commit explícito

    def send_email(self, to_email: str, new_password: str):
        """Envia e-mail com a nova senha via SendGrid"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #333;">Clara App - Recuperação de Senha</h2>
                <p>Olá!</p>
                <p>Sua nova senha temporária é:</p>
                <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <code style="font-size: 18px; color: #d63031; font-weight: bold;">{new_password}</code>
                </div>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">Este é um e-mail automático. Não responda.</p>
            </body>
        </html>
        """
        
        message = Mail(
            from_email=self.email_from,
            to_emails=to_email,
            subject='Clara App - Recuperação de Senha 🔐',
            html_content=html_content
        )
        
        sg = SendGridAPIClient(self.sendgrid_key)
        response = sg.send(message)
        
        if response.status_code not in [200, 202]:
            raise Exception(f"Falha ao enviar e-mail: {response.status_code}")

    def recover(self, email: str):
        """
        Processa recuperação de senha completa:
        1. Verifica se e-mail existe no banco
        2. Gera nova senha aleatória
        3. Atualiza no banco (usando o MESMO hash do login!)
        4. Envia e-mail com a nova senha
        """
        # 1. Busca usuário
        user = self.find_user_by_email(email)
        if not user:
            return False, "E-mail não cadastrado no sistema"
        
        user_id, user_email = user
        
        # 2. Gera nova senha
        new_pass = self.generate_password()
        
        # 3. Hash com a MESMA função usada no cadastro ✅
        hashed = get_password_hash(new_pass)
        
        # 4. Atualiza no banco
        self.update_user_password(user_id, hashed)
        
        # 5. Envia e-mail
        try:
            self.send_email(user_email, new_pass)
            return True, "Senha redefinida com sucesso. Verifique seu e-mail."
        except Exception as e:
            print(f"Erro ao enviar e-mail: {e}")
            return False, "Erro ao enviar e-mail. Tente novamente."