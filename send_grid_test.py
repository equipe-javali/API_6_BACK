import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()  # carrega .env na raiz do projeto

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
# opcional: defina TEST_RECEIVER no .env para outro destinatário de teste
EMAIL_TO = os.getenv("TEST_RECEIVER", EMAIL_FROM)

if not SENDGRID_API_KEY or not EMAIL_FROM:
    print("Faltando SENDGRID_API_KEY ou EMAIL_FROM no .env")
    raise SystemExit(1)

message = Mail(
    from_email=EMAIL_FROM,
    to_emails=EMAIL_TO,
    subject="Teste de envio de e-mail - Projeto",
    html_content="<p>Este é um teste de envio de e-mail via SendGrid.</p>"
)

try:
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    print("Status Code:", response.status_code)
    print("Body:", response.body)
    print("Headers:", response.headers)
    print(f"E-mail enviado para {EMAIL_TO}")
except Exception as e:
    print("Erro ao enviar e-mail:", e)