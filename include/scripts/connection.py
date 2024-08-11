from airflow.models import Connection
from airflow import settings
from airflow.utils.db import provide_session

# TODO: Need to test this function

@provide_session
def create_connection(session=None):
    c = Connection(
        conn_id="postgres_localhost",
        conn_type="postgres",
        description="localhost postgres connection in a docker for main database",
        host="host.docker.internal",
        login="postgres",
        password="postgres",
    )
    session.add(c)
    session.commit()


if __name__ == "__main__":
    create_connection()
