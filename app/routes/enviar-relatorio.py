from fastapi import APIRouter, Depends, HTTPException
from app.models.models import Relatorio
from app.services.services import get_current_user, admin_required, enviar_email
from app.db.db_simulado import usuarios

router = APIRouter()

@router.post("/enviar-relatorio")
def enviar_relatorio(relatorio: Relatorio, current_user=Depends(get_current_user)):
    """Envia boletim por e-mail para todos os usuários inscritos"""
    admin_required(current_user)

    boletim = f"{relatorio.titulo}\n\n{relatorio.conteudo}"
    inscritos = [u for u in usuarios if u["recebe_boletim"]]

    if not inscritos:
        raise HTTPException(status_code=404, detail="Nenhum usuário inscrito")

    for user in inscritos:
        enviar_email(user["email"], relatorio.titulo, boletim)

    return {"status": "ok", "enviados": [u["email"] for u in inscritos]}
