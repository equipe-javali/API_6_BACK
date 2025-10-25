from datetime import datetime, timedelta
from db.neon_db import NeonDB

def _ler_periodo_banco() -> tuple[datetime | None, datetime | None]:
    """Lê o último período salvo no Neon"""
    try:
        with NeonDB() as db:
            row = db.fetchone("""
                SELECT data_inicio, data_fim
                FROM semanaboletim
                ORDER BY id DESC
                LIMIT 1
            """)
            if not row:
                return None, None
            data_inicio, data_fim = row
            return data_inicio, data_fim
    except Exception as e:
        print(f"⚠️ Erro ao ler período do banco: {e}")
        return None, None


def _salvar_periodo_banco(data_inicio: datetime, data_fim: datetime):
    """Salva novo período no Neon"""
    try:
        with NeonDB() as db:
            db.execute("""
                INSERT INTO semanaboletim (data_inicio, data_fim)
                VALUES (%s, %s)
            """, [data_inicio.date(), data_fim.date()])
            db.commit()
            print(f"Período salvo no banco: {data_inicio:%d/%m/%Y} → {data_fim:%d/%m/%Y}")
    except Exception as e:
        print(f"Erro ao salvar período no banco: {e}")
