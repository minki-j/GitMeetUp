import os
import re
import json
import pendulum

from airflow.decorators import dag, task
from airflow.models import Variable

from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from airflow.providers.postgres.hooks.postgres import PostgresHook

from dags.common_tasks.get_column_names import get_col_names
from include.utils.sql_functions import (
    select_data_with_condition,
    create_or_update_table,
    insert_data,
)
from include.github_api_call.request import github_api_request
from include.llm_analysis.main_graph import langgraph_app

@dag(
    schedule="@once",
    start_date=pendulum.datetime(2024, 1, 1, tz="America/Montreal"),
    catchup=False,
    doc_md=__doc__,
    default_args={"owner": "Minki", "retries": 0},
    tags=["llm"],
)
def analyze_repositories_dag():

    @task()
    def get_repositories():
        # Get all repositories from postgres
        hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
        connection = hook.get_conn()

        with connection.cursor() as cursor:
            repo_info = cursor.execute("SELECT id, full_name, commits_url, description, clone_url, fork, languages_full_list, packages_used, tree FROM repositories")

        return repo_info

    @task()
    def analyze(**context):
        repo_info = context["ti"].xcom_pull(task_ids="get_repositories")
        for repo in repo_info:
            result = langgraph_app.invoke(repo)
            print(f"==>> result: {result}")
            break
        

    get_repositories() >> analyze()

analyze_repositories_dag()
