"""
## Scrapping and filtering github accounts and repositories

This DAG is used to scrape and filter github accounts and repositories. The DAG is scheduled to run every hour until it finished scraping all the accounts and repositories in a given location.
"""

import os
import time
import requests
from typing import List
from psycopg2 import sql
from pendulum import datetime, now

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
from airflow.providers.github.operators.github import GithubOperator

from dags.utils.fetch_users import fetch_github_acocunts_by_date_location
from dags.utils.date_utils import generate_date_intervals
from dags.utils.sql import create_or_update_table, insert_data


@dag(
    start_date=datetime(2024, 1, 1),
    schedule="@once",
    catchup=False,
    doc_md=__doc__,
    default_args={"owner": "Minki"},
    tags=["github"],
)
def fetch_accounts_dag(location="montreal"):

    # TODO: Save date intervals into postgres rather than keep tracking next_query_date_idx in Variable
    # @task()
    # def get_date_intervals() -> List[str]:
    #     return generate_date_intervals(interval_days=30)

    # TODO: use operators if possible to simplify the code
    # get_users = GithubOperator(
    #     github_conn_id="github_default",
    #     github_method="get_users",
    #     github_method_args={
    #         "q": f"location:{location} created:{date}",
    #         "page": 1,
    #         "per_page": 100,
    #         "sort": "joined",
    #         "order": "desc",
    #     },
    #     result_processor="None",
    # )

    @task(outlets=[Dataset("github_accounts")])
    def fetch_accounts(location, **context):
        print("==> fetch_accounts")
        """
        This task uses the requests library to retrieve a list of Github accounts
        in a given location. The results are pushed to XCom with a specific key
        so they can be used in a downstream pipeline. The task returns a list
        of Github accounts to be used in the next task.
        """
        Variable.set(f"is_query_for_{location}_done", False)

        # TODO: save date intervals into postgres with is_fetched_in_{location} column
        # location = "montreal"
        dates = generate_date_intervals(interval_days=30)
        accounts = []
        next_query_date_idx = int(
            Variable.get(f"next_query_date_idx_{location}", default_var=0)
        )

        for idx, date in enumerate(dates):
            if idx < next_query_date_idx:
                continue

            # # FOR FAST DEBUGGING
            # if idx > 0:
            #     print("DEBUG MODE: breaking after 1 iterations")
            #     next_query_date_idx = idx
            #     break

            (
                accounts_in_date,
                overflowed_date,
                reached_rate_limit,
                rate_limit_reset_time,
            ) = fetch_github_acocunts_by_date_location(location, date)

            if accounts_in_date:
                accounts.extend(accounts_in_date)

            if len(overflowed_date) > 0:
                overflowed_date_from_var = Variable.get(
                    f"overflowed_date_{location}", default_var=[]
                )
                overflowed_date_from_var.extend(overflowed_date)
                Variable.set(f"overflowed_date_{location}", overflowed_date_from_var)

            if reached_rate_limit:
                next_query_date_idx = idx # Don't add 1 since we might miss some pages from the current date interval
                Variable.set(f"next_query_date_idx_{location}", next_query_date_idx)
                break

            if idx == len(dates) - 1:
                Variable.delete(f"next_query_date_idx_{location}")
                print("==>> All queries are done, setting Variable to True")
                Variable.set(f"is_query_for_{location}_done", True)
                break

        print(
            f"processed {next_query_date_idx - 1} out of {len(dates)} / {dates[next_query_date_idx - 1]}"
        )
        print(f"collected user: {len(accounts)}")

        if len(accounts) > 0:
            hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
            connection = hook.get_conn()

            with connection.cursor() as cursor:
                create_or_update_table(
                    cursor,
                    accounts,
                    table_name="github_accounts",
                )
                insert_data(
                    cursor,
                    accounts,
                    table_name="github_accounts",
                )

            connection.commit()
            connection.close()

        return {"rate_limit_reset_time": rate_limit_reset_time}

    @task.branch(task_id="is_query_not_completed")
    def is_query_not_completed(location):
        is_query_completed_str = Variable.get(f"is_query_for_{location}_done", "False")
        is_query_completed = is_query_completed_str == "True"

        if is_query_completed:
            print("==>> Query is done, branching to trigger_fetch_accounts_dag")
            return "trigger_filter_accounts_dag"
        print("==>> Query is not done, continuing the downstream tasks")
        return "wait_until_rate_limit_rest"

    @task
    def wait_until_rate_limit_rest(xcom):
        rate_limit_reset_time = xcom["rate_limit_reset_time"]
        sleep_time = int(rate_limit_reset_time) - int(time.time())
        if sleep_time > 0:
            print(f"==>> Sleeping for {sleep_time} seconds")
            time.sleep(sleep_time + 1)

    trigger_fetch_accounts_dag = TriggerDagRunOperator(
        start_date=datetime(2024, 1, 1),
        task_id="trigger_self_dag",
        trigger_dag_id="fetch_accounts_dag",
    )

    trigger_filter_accounts_dag = TriggerDagRunOperator(
        start_date=datetime(2024, 1, 1),
        task_id="trigger_filter_accounts_dag",
        trigger_dag_id="filter_accounts_dag",
    )

    fetch_accounts_instance = fetch_accounts(location)
    wait_until_rate_limit_reset_instance = wait_until_rate_limit_rest(
        fetch_accounts_instance
    )
    is_query_not_completed_instance = is_query_not_completed(location)

    (
        fetch_accounts_instance
        >> is_query_not_completed_instance
        >> wait_until_rate_limit_reset_instance
        >> trigger_fetch_accounts_dag
    )

    is_query_not_completed_instance >> trigger_filter_accounts_dag


fetch_accounts_dag()
