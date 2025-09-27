from fastapi import APIRouter, HTTPException, UploadFile, File
from services.csv_service import CsvService
from models.csv_models import CsvTextRequest

router = APIRouter(
    prefix="/csv",
    tags=["csv"],
    responses={404: {"description": "Não encontrado"}},
)

csv_service = CsvService()

@router.post("/faturamento/upload")
async def upload_csv_faturamento(file: UploadFile = File(...)):
    """Faz upload de um arquivo CSV de faturamento e processa os dados."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser um CSV")
    
    try:
        content = await file.read()
        csv_content = content.decode('utf-8')
        return csv_service.processar_csv_faturamento(csv_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")

@router.post("/estoque/upload")
async def upload_csv_estoque(file: UploadFile = File(...)):
    """Faz upload de um arquivo CSV de estoque e processa os dados."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser um CSV")
    
    try:
        content = await file.read()
        csv_content = content.decode('utf-8')
        return csv_service.processar_csv_estoque(csv_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")

@router.post("/faturamento/text")
def processar_csv_faturamento_text(request: CsvTextRequest):
    """Processa CSV de faturamento a partir de texto."""
    return csv_service.processar_csv_faturamento(request.csv_content)

@router.post("/estoque/text")
def processar_csv_estoque_text(request: CsvTextRequest):
    """Processa CSV de estoque a partir de texto."""
    return csv_service.processar_csv_estoque(request.csv_content)
