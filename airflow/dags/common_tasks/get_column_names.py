from airflow.models import Variable
from airflow.providers.postgres.hooks.postgres import PostgresHook

def get_col_names(table_name):
    """
    Get column names of the table from the database.
    By defualt, Postgres returns a nested list of column names.
    This function flattens the list and returns a list of column names, 
    making the downstream tasks easier to work with.
    """
    hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
    connection = hook.get_conn()
    
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
        col_names = cursor.fetchall()

    # flatten and return
    return [item for sublist in col_names for item in sublist]
