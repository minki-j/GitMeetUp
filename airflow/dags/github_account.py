"""
## Scrapping and filtering github accounts and repositories

This DAG is used to scrape and filter github accounts and repositories. The DAG is scheduled to run every hour until it finished scraping all the accounts and repositories in a given location.
"""

from airflow import Dataset
from airflow.decorators import dag, task

from airflow.operators.bash import BashOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from pendulum import datetime
import requests
import os
from dags.utils.fetch_users import fetch_github_acocunts_by_date_location
from dags.utils.date_utils import generate_date_intervals
from dags.utils.convert_to_sql_data_type import convert_to_sql_data_type
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
def fetch_accounts():
    # create_table = PostgresOperator(
    #     task_id="create_table",
    #     database=None,
    #     hook_params=None,
    #     retry_on_failure="True",
    #     sql="""
    #     CREATE TABLE IF NOT EXISTS my_table (
    #         id SERIAL PRIMARY KEY,
    #         name VARCHAR(50),
    #         value INTEGER
    #     );
    #     """,
    #     autocommit="False",
    #     parameters=None,
    #     split_statements=None,
    #     return_last="True",
    #     show_return_value_in_logs="False",
    #     postgres_conn_id="postgres_localhost",
    #     runtime_parameters=None,
    # )

    fetch_data = PostgresOperator(
        task_id="fetch_data",
        database=None,
        hook_params=None,
        retry_on_failure="True",
        sql="""
        SELECT * FROM github_accounts;
        """,
        autocommit="False",
        parameters=None,
        split_statements=None,
        return_last="True",
        show_return_value_in_logs="False",
        postgres_conn_id="postgres_localhost",
        runtime_parameters=None,
    )

    @task(outlets=[Dataset("github_accounts")])
    def get_accounts(**context):
        print("==> get_accounts")
        """
        This task uses the requests library to retrieve a list of Github accounts
        in a given location. The results are pushed to XCom with a specific key
        so they can be used in a downstream pipeline. The task returns a list
        of Github accounts to be used in the next task.
        """
        hook = PostgresHook(postgres_conn_id="postgres_localhost")
        connection = hook.get_conn()
        cursor = connection.cursor()

        location = "montreal"
        dates = generate_date_intervals(interval_days=60)
        accounts = []

        next_query_date_idx = int(Variable.get(f"next_query_date_idx_{location}", default_var=0))
        print(f"==>> next_query_date_idx: {next_query_date_idx}")

        for idx, date in enumerate(dates):
            if idx < next_query_date_idx:
                continue
            accounts_in_date, log, reached_rate_limit, rate_limit_reset_time = (
                fetch_github_acocunts_by_date_location(location, date)
            )
            accounts.extend(accounts_in_date)

            if reached_rate_limit:
                next_query_date_idx = idx + 1
                Variable.set(f"next_query_date_idx_{location}", next_query_date_idx)
                break
            if idx == len(dates) - 1:
                Variable.delete(f"next_query_date_idx_{location}")

        print(f"==>> accounts: {len(accounts)}")

        # Create table dynamically based on the keys and data types of the first account dictionary
        column_definitions = ", ".join(
            [
                f"{column} {convert_to_sql_data_type(type(value))}"
                for column, value in accounts[0].items()
            ]
        )
        create_table_query = f"CREATE TABLE IF NOT EXISTS github_accounts ({column_definitions});"
        cursor.execute(create_table_query)
        connection.commit()

        if accounts:
            # Insert data into the table
            for account in accounts:
                columns = account.keys()
                values = [account[column] for column in columns]
                placeholders = ', '.join(['%s'] * len(values))  # Using %s as placeholder for psycopg2
                insert_query = f"INSERT INTO github_accounts ({', '.join(columns)}) VALUES ({placeholders})"
                cursor.execute(insert_query, values)
                connection.commit()
        
        cursor.close()
        connection.close()

        return rate_limit_reset_time

    wait_for_one_minute = BashOperator(
        task_id="wait_for_one_minute",
        bash_command="sleep 60",
    )

    trigger_get_accounrt = TriggerDagRunOperator(
        start_date=datetime(2024, 1, 1),
        # logical_date=rate_limit_reset_time,
        task_id="trigger_self_dag",
        trigger_dag_id="fetch_accounts",
        conf={"location": "montreal"},
    )

    get_accounts() >> fetch_data >> wait_for_one_minute >> trigger_get_accounrt


fetch_accounts()
