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
        self.cursor.close()
        self.conn.close()
    
    def __cursor(self):
        if self.cursor:
            return self.cursor
        return self.conn.cursor()

    def query(self, sql: str, params: list | None = None) -> list[tuple]:
        cursor = self.__cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()
    
    def fetchone(self, sql: str, params: list | None = None) -> tuple:
        cursor = self.__cursor()
        cursor.execute(sql, params)
        return cursor.fetchone()
    
    def commit(self):
        self.conn.commit()
