import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from dotenv import load_dotenv

load_dotenv()
BREVO_KEY = os.getenv("BREVO_KEY")


configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = BREVO_KEY

api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

def enviar_email(destinatarios: list[str], assunto: str, conteudo_html: str):
    """Envia e-mail para uma lista de destinatários"""
    try:
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": d} for d in destinatarios],
            sender={"email": "dsmjavali@gmail.com", "name": "Equipe Javali Corporations"},
            subject=assunto,
            html_content=conteudo_html
        )

        response = api_instance.send_transac_email(email)

        print("Resposta do Brevo para envio:", response.to_dict())

        return {"status": "sucesso", "response": response.to_dict()}
    except ApiException as e:
        return {"status": "erro", "mensagem": str(e)}
