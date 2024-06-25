import os
import time
from psycopg2 import sql
from datetime import datetime, timedelta


from airflow import Dataset
from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.models.xcom_arg import XComArg
from airflow.operators.empty import EmptyOperator
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

from dags.utils.sql import (
    add_new_columns,
    select_data_with_condition,
    get_existing_columns,
    update_table_multiple_rows,
)
from dags.utils.filter_users_in_parallel import filter_users_in_parallel


@dag(
    start_date=datetime(2024, 1, 1),
    schedule="@once",
    catchup=False,
    doc_md=__doc__,
    default_args={"owner": "Minki", "retries": 0},
    tags=["github"],
)
def filter_accounts_dag(table_name="github_accounts", threshold=14):
    @task()
    def filter_accounts(threshold, table_name, **context):
        print("==> filter_accounts")
        print("table_name: ", table_name)

        # get users from postgres
        hook = PostgresHook(postgres_conn_id=Variable.get("postgres_conn_id"))
        connection = hook.get_conn()

        with connection.cursor() as cursor:
            existing_columns = get_existing_columns(cursor, table_name)
            if "status" not in existing_columns:
                add_new_columns(
                    cursor,
                    table_name=table_name,
                    example={"status": "active"},
                )

            account_id_and_urls = select_data_with_condition(
                cursor,
                table_name=table_name,
                select_condition="id, url",
                where_condition="status IS NULL",
            )

        connection.commit()

        if not account_id_and_urls:
            print("No accounts to filter.")
            return

        print("accounts: ", account_id_and_urls[:3])
        print("accounts len: ", len(account_id_and_urls))

        result = filter_users_in_parallel(account_id_and_urls, threshold)
        print("active: ",result["active"])

        with connection.cursor() as cursor:
            for status, user_info_list in result.items():
                if len(user_info_list) == 0:
                    continue
                data = [user_info | {"status": status} for user_info in user_info_list]
                update_table_multiple_rows(
                    cursor,
                    table_name=table_name,
                    data=data,
                    identifier="id",
                )

        connection.commit()

    filter_accounts_instance = filter_accounts(
        threshold=threshold, table_name=table_name
    )


filter_accounts_dag()


# UPdate table set price = 600 where productname = "pants"
