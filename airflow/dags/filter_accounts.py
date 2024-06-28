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
    template_searchpath=Variable.get("TEMPLATE_SEARCHPATH"),
)
def filter_accounts_dag(table_name="github_accounts", threshold=14):

    get_column_names = PostgresOperator(
        task_id="get_column_names",
        sql="get_column_names.sql",
        postgres_conn_id=Variable.get("POSTGRES_CONN_ID"),
        parameters={"table_name": table_name},
    )

    @task()
    def filter_accounts(threshold, table_name, **context):
        print("==> filter_accounts")

        # get xcom variable from existing_columns
        existing_columns = context["ti"].xcom_pull(task_ids="get_column_names")

        # flatten the list
        existing_columns = [item for sublist in existing_columns for item in sublist]

        # get users from postgres
        hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
        connection = hook.get_conn()

        with connection.cursor() as cursor:
            if "created_at" not in existing_columns:
                query = f"SELECT id, url FROM {table_name}"
                try:
                    cursor.execute(query)
                except Exception as e:
                    print(f"Failed to execute query: {query}")
                account_infos =  cursor.fetchall()

            else:
                account_infos = select_data_with_condition(
                    cursor,
                    table_name=table_name,
                    select_condition="id, url",
                    where_condition="created_at IS NULL",
                )

            fetched_users, is_finished, reset_time = filter_users_in_parallel(
                account_infos
            )
            Variable.set(f"is_filter_for_filter_done", str(is_finished))
            Variable.set(f"rate_limit_reset_time", str(reset_time))

            update_table_multiple_rows(
                cursor, table_name, existing_columns, fetched_users, "id"
            )

        connection.commit()

        return {"is_finished": is_finished, "reset_time": reset_time}

    @task.branch(task_id="is_query_not_completed")

    def is_finished():
        is_finished_str = Variable.get(f"is_filter_for_filter_done", "False")
        is_finished = is_finished_str == "True"

        if is_finished:
            print("==>> Filter is done, branching to end")
            return "end"
        print("==>> Filter is not done, continuing the downstream tasks")
        return "wait_until_rate_limit_rest"

    @task
    def wait_until_rate_limit_rest():
        rate_limit_reset_time = Variable.get(f"rate_limit_reset_time", 0)
        if rate_limit_reset_time == 0:
            return
        sleep_time = int(rate_limit_reset_time) - int(time.time())
        if sleep_time > 0:
            print(f"==>> Sleeping for {int(sleep_time/60)} minutes")
            time.sleep(sleep_time + 1)

    trigger_filter_accounts_dag = TriggerDagRunOperator(
        start_date=datetime(2024, 1, 1),
        task_id="trigger_self_dag",
        trigger_dag_id="filter_accounts_dag",
    )

    end_task = EmptyOperator(task_id="end")

    filter_accounts_instance = filter_accounts(
        threshold=threshold, table_name=table_name
    )

    get_column_names >> filter_accounts_instance >> is_finished() >> wait_until_rate_limit_rest() >> trigger_filter_accounts_dag

    is_finished() >> end_task

filter_accounts_dag()
