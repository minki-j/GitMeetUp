"""
## Scrapping and filtering github accounts and repositories

This DAG is used to scrape and filter github accounts and repositories. The DAG is scheduled to run every hour until it finished scraping all the accounts and repositories in a given location.
"""

import os
import time
import requests
from typing import List
from psycopg2 import sql
import pendulum

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

from include.github_api_call.fetch_users import fetch_github_acocunts_by_date_location
from dags.utils.date_utils import generate_date_intervals
from dags.utils.sql import create_or_update_table, insert_data


@dag(
    start_date=pendulum.datetime(2024, 1, 1, tz="America/Toronto"),
    schedule="@once",
    catchup=False,
    doc_md=__doc__,
    default_args={
        "owner": "Minki",
        "retries": 1,
        "retry_delay": pendulum.duration(seconds=10),
    },
    tags=["github"],
)
def search_users_by_location_dag(location: str = "montreal"):
    @task()
    def fetch_users(**context):
        print("==> fetch_users")
        location = context["dag_run"].conf.get("location")
        Variable.set(f"is_query_for_{location}_done", False)
        dates = generate_date_intervals(interval_days=30)
        accounts = []
        next_query_date_idx = int(
            Variable.get(f"next_query_date_idx_{location}", default_var=0)
        )
        reached_rate_limit = False
        rate_limit_reset_time = None

        for idx, date in enumerate(dates):
            if idx < next_query_date_idx:
                continue

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
                print(
                    f"total num of overflowed_date_{location}: ",
                    len(overflowed_date_from_var),
                )
                Variable.set(f"overflowed_date_{location}", overflowed_date_from_var)

            if reached_rate_limit:
                next_query_date_idx = idx
                Variable.set(f"next_query_date_idx_{location}", next_query_date_idx)
                Variable.set(
                    f"github_search_api_reset_utc_dt",
                    pendulum.from_timestamp(
                        rate_limit_reset_time, tz="UTC"
                    ).to_datetime_string(),
                )
                break
            else:
                Variable.delete(f"github_search_api_reset_utc_dt")

            if idx == len(dates) - 1:
                Variable.delete(f"next_query_date_idx_{location}")
                print("==>> All queries are done, setting Variable to True")
                Variable.set(f"is_query_for_{location}_done", True)
                break

            # if len(accounts) > 0:
            #     print("DEBUG MODE: breaking after 1 acocunt")
            #     next_query_date_idx = idx
            #     break

        print(
            f"processed {next_query_date_idx - 1} out of {len(dates)} / until {dates[next_query_date_idx - 1]}"
        )
        print(f"collected user: {len(accounts)}")

        return accounts

    @task()
    def update_db(**context):
        print("==> update_db")
        accounts = context["ti"].xcom_pull(task_ids="fetch_users")
        if len(accounts) > 0:
            hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
            connection = hook.get_conn()
            with connection.cursor() as cursor:
                create_or_update_table(cursor, accounts, table_name="github_accounts")
                insert_data(cursor, accounts, table_name="github_accounts")
            connection.commit()
            connection.close()

    @task.branch(task_id="is_query_not_completed")
    def is_query_not_completed(**context):
        print("==> is_query_not_completed")
        location = context["dag_run"].conf.get("location")
        is_query_completed_str = Variable.get(f"is_query_for_{location}_done", "False")
        is_query_completed = is_query_completed_str == "True"

        if is_query_completed:
            print(
                "==>> Query is done, branching to trigger_search_users_by_location_dag"
            )
            return "trigger_fetch_user_full_info_dag"

        print("==>> Query is not done, continuing the downstream tasks")
        return "trigger_self_dag"

    trigger_self_dag = TriggerDagRunOperator(
        logical_date=(
            pendulum.parse(Variable.get(f"github_search_api_reset_utc_dt"))
            if Variable.get(f"github_search_api_reset_utc_dt", None)
            else pendulum.now()
        ),
        task_id="trigger_self_dag",
        trigger_dag_id="search_users_by_location_dag",
        conf={"location": '{{ dag_run.conf.get("location") }}'},
    )

    trigger_fetch_user_full_info_dag = TriggerDagRunOperator(
        start_date=pendulum.datetime(2024, 1, 1, tz="America/Toronto"),
        task_id="trigger_fetch_user_full_info_dag",
        trigger_dag_id="fetch_user_full_info_dag",
    )

    is_query_not_completed_task = is_query_not_completed()

    fetch_users() >> update_db() >> is_query_not_completed_task >> trigger_self_dag
    is_query_not_completed_task >> trigger_fetch_user_full_info_dag


search_users_by_location_dag()
