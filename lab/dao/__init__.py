import os

import psycopg


class Connection:
    def __init__(
        self,
        database: str = os.getenv('DATABASE', 'postgres'),
        user: str = os.getenv('PG_USER', 'postgres'),
        password: str = os.getenv('PASSWORD', 'postgres'),
        host: str = os.getenv('HOST', 'localhost'),
        port: int = int(os.getenv('PORT', '5433')),
    ):
        self.database = database
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.connection = None

    def __enter__(self):
        self.connection = psycopg.connect(
            dbname=self.database,
            user=self.user,
            host=self.host,
            password=self.password,
            port=self.port,
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                print(f'Erro ao fechar a conexão: {e}')
                raise

    def select(self, script_sql: str, parameters: list = []):
        with self.connection.cursor() as cursor:
            cursor.execute(script_sql, parameters)
            return cursor.fetchall()

    def exec(self, script_sql: str, parameters: list = []):
        with self.connection.cursor() as cursor:
            cursor.execute(script_sql, parameters)
            self.connection.commit()

    def exec_with_result(self, script_sql: str, parameters: list = []):
        with self.connection.cursor() as cursor:
            cursor.execute(script_sql, parameters)
            self.connection.commit()
            return cursor.fetchone()
