import psycopg2

class NeonDB:
    def __init__(self):
        self.conn = psycopg2.connect("postgresql://neondb_owner:npg_mR2nM7oqVNTr@ep-plain-queen-ad3ji27w-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")
        self.cursor = self.conn.cursor()

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.__close()

    def __del__(self):
        self.__close()
    
    def __close(self):
        try: self.cursor.close()
        except: pass
        try: self.conn.close()
        except: pass
    
    def __cursor(self):
        return self.cursor or self.conn.cursor()

    def query(self, sql: str, params: list | None = None) -> list[tuple]:
        c = self.__cursor()
        c.execute(sql, params)
        return c.fetchall()
    
    def fetchone(self, sql: str, params: list | None = None) -> tuple:
        c = self.__cursor()
        c.execute(sql, params)
        return c.fetchone()
    
    def execute(self, sql: str, params: list | None = None) -> None:
        c = self.__cursor()
        c.execute(sql, params)
    
    def fetchall(self, sql: str, params: list | None = None) -> list[tuple]:
        cursor = self.__cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()
    
    def commit(self):
        self.conn.commit()

def get_db():
    db = NeonDB()
    try:
        yield db
    finally:
        db.__exit__(None, None, None)

def execute_query(query: str):
    """Executa uma query SQL e retorna os resultados formatados"""
    with NeonDB() as db:
        try:
            # Se for SELECT, retornar dados formatados
            if query.strip().upper().startswith('SELECT'):
                cursor = db._NeonDB__cursor()
                cursor.execute(query)
                
                # Obter nomes das colunas
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # Obter resultados
                results = cursor.fetchall()
                
                # Converter para lista de dicionários
                formatted_results = []
                for row in results:
                    row_dict = dict(zip(columns, row))
                    formatted_results.append(row_dict)
                
                return formatted_results
            else:
                # Para INSERT, UPDATE, DELETE
                db.execute(query)
                db.commit()
                return {"success": True}
                
        except Exception as e:
            raise Exception(f"Erro ao executar query: {str(e)}")

