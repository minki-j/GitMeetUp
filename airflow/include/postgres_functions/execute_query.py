
from airflow.providers.postgres.hooks.postgres import PostgresHook

from airflow.models import Variable

def execute_postgres_query(query: str):
    hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
    connection = hook.get_conn()

    with connection.cursor() as cursor:
        cursor.execute(query)
    
    connection.commit()