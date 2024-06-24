"""
## Scrapping and filtering github accounts and repositories

This DAG is used to scrape and filter github accounts and repositories. The DAG is scheduled to run every hour until it finished scraping all the accounts and repositories in a given location.
"""

from airflow import Dataset
from airflow.decorators import dag, task
from airflow.models.xcom_arg import XComArg
from airflow.operators.empty import EmptyOperator
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from pendulum import datetime, now
import requests
import os
import time
from dags.utils.fetch_users import fetch_github_acocunts_by_date_location
from dags.utils.date_utils import generate_date_intervals
from dags.utils.sql import create_or_update_table, insert_data
from psycopg2 import sql
from airflow.models import Variable


@dag(
    start_date=datetime(2024, 1, 1),
    schedule="@once",
    catchup=False,
    doc_md=__doc__,
    default_args={"owner": "Minki", "retries": 0},
    tags=["github"],
)
def fetch_accounts(location="montreal"):

    @task(outlets=[Dataset("github_accounts")])
    def get_accounts(location, **context):
        print("==> get_accounts")
        """
        This task uses the requests library to retrieve a list of Github accounts
        in a given location. The results are pushed to XCom with a specific key
        so they can be used in a downstream pipeline. The task returns a list
        of Github accounts to be used in the next task.
        """
        Variable.set(f"is_query_for_{location}_done", False)

        # location = "montreal"
        dates = generate_date_intervals(interval_days=60)
        accounts = []
        next_query_date_idx = int(
            Variable.get(f"next_query_date_idx_{location}", default_var=0)
        )
        print("next_query_date_idx: ", next_query_date_idx, "out of", len(dates))

        for idx, date in enumerate(dates):
            if idx < next_query_date_idx:
                continue
            accounts_in_date, log, reached_rate_limit, rate_limit_reset_time = (
                fetch_github_acocunts_by_date_location(location, date)
            )
            if accounts_in_date:
                accounts.extend(accounts_in_date)
            if reached_rate_limit:
                next_query_date_idx = idx + 1
                Variable.set(f"next_query_date_idx_{location}", next_query_date_idx)
                break
            if idx == len(dates) - 1:
                Variable.delete(f"next_query_date_idx_{location}")
                print("==>> All queries are done, setting Variable to True")
                Variable.set(f"is_query_for_{location}_done", True)
                break

        print(f"==>> accounts: {len(accounts)}")

        hook = PostgresHook(postgres_conn_id="postgres_localhost")
        connection = hook.get_conn()

        create_or_update_table(connection, accounts, table_name="github_accounts")
        insert_data(connection, accounts, table_name="github_accounts")

        connection.close()

        return {"rate_limit_reset_time": rate_limit_reset_time}

    @task
    def fetch_data(
        table_name="github_accounts",
        postgres_conn_id="postgres_localhost",
        autocommit=False,
        return_last=True,
    ):
        hook = PostgresHook(postgres_conn_id=postgres_conn_id)
        # sql = f"SELECT * FROM {table_name};"
        sql = f"SELECT * FROM github_accounts;"

        with hook.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                if not autocommit:
                    conn.commit()
                if return_last:
                    result = cur.fetchall()
                    print(f"==>> result: {result}")
                    return result
                else:
                    return None

    @task.short_circuit()
    def is_query_not_completed(location):
        # Correctly retrieve and convert the variable to a boolean
        is_query_completed_str = Variable.get(f"is_query_for_{location}_done", "False")
        is_query_completed = is_query_completed_str == "True"

        if is_query_completed:
            print("==>> Query is done, skipping the downstream tasks. Return False")
            return False
        print("==>> Query is not done, continuing the downstream tasks. Return True")
        return True

    @task
    def wait_until_rate_limit_rest(xcom):
        rate_limit_reset_time = xcom["rate_limit_reset_time"]
        sleep_time = int(rate_limit_reset_time) - int(time.time())
        if sleep_time > 0:
            print(f"==>> Sleeping for {sleep_time} seconds")
            time.sleep(sleep_time + 1)

    trigger_get_account = TriggerDagRunOperator(
        start_date=datetime(2024, 1, 1),
        task_id="trigger_self_dag",
        trigger_dag_id="fetch_accounts",
    )

    get_accounts_result = get_accounts(location)
    wait_until_rate_limit_rest_task = wait_until_rate_limit_rest(get_accounts_result)

    (
        get_accounts_result
        >> fetch_data(location)
        >> is_query_not_completed(location)
        >> wait_until_rate_limit_rest_task
        >> trigger_get_account
    )


fetch_accounts()
