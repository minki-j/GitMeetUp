import os
import re
import json
import subprocess
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
    create_document_table_with_repo_id_as_fk,
    insert_document,
)
from include.github_api_call.request import github_api_request
from include.llm_analysis.main_graph import langgraph_app
from include.utils.convert_column_names import convert_postgres_to_state_schema


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
        columns = [
            "id",
            "name",
            "commits_url",
            "description",
            "packages_used",
            "tree",
            "clone_url",
            "fork",
            "languages_full_list",
        ]
        packages = ["langchain"]

        hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
        connection = hook.get_conn()

        with connection.cursor() as cursor:
            where_condition = "WHERE " + " AND ".join(
                [f"packages_used LIKE '%{package_name}%'" for package_name in packages]
            )
            if "analyzed_at" in get_col_names("github_repositories"):
                where_condition += " AND analyzed_at IS NULL"
            query = f"SELECT {', '.join(columns)} FROM github_repositories {where_condition} LIMIT 1;"
            print(f"==>> query: {query}")
            repo_info = cursor.execute(query)

            repo_info = cursor.fetchone()

        repo_info = dict(zip(columns, repo_info))

        return convert_postgres_to_state_schema(repo_info)

    @task()
    def analyze(**context):
        repo = context["ti"].xcom_pull(task_ids="get_repositories")

        clone_url = repo["clone_url"]
        target_dir = os.path.join(
            "./cache/cloned_repositories", repo["title"].replace("/", "_")
        )

        # remove the directory if it already exists
        result = subprocess.run(
            "rm -rf " + target_dir,
            capture_output=True,
            check=True,
            text=True,
            shell=True,
        )

        #remove cache
        result = subprocess.run(
            "rm -rf ./cache/*",
            capture_output=True,
            check=True,
            text=True,
            shell=True,
        )

        try:
            print("start cloning ", clone_url)
            result = subprocess.run(
                "git clone " + clone_url + " " + target_dir,
                capture_output=True,
                check=True,
                text=True,
                shell=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error cloning repository: {e}")
            print(f"Return code: {e.returncode}")
            print(f"Output: {e.output}")
            print(f"Error output: {e.stderr}")

        repo["repo_root_path"] = target_dir

        result = langgraph_app.invoke(repo)
        print(f"==>> result: {result}")
        print("Analysis: ", result["final_hypotheses"])
        analysis = {
            "id": repo["id"],
            "final_hypotheses": "\n".join(result["final_hypotheses"]),
        }

        return analysis

    @task()
    def update_db(**context):
        print("==> update_db")
        analysis_results = context["ti"].xcom_pull(task_ids="analyze")

        hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
        connection = hook.get_conn()
        with connection.cursor() as cursor:
            create_document_table_with_repo_id_as_fk(
                cursor,
                "repo_analysis",
            )
            insert_document(
                cursor,
                "repo_analysis",
                analysis_results["id"],
                [analysis_results],
            )

            # add analyzed_at column to github_repositories
            columns = get_col_names("github_repositories")
            if "analyzed_at" not in columns:
                cursor.execute(
                    "ALTER TABLE github_repositories ADD COLUMN analyzed_at TIMESTAMP"
                )
                print("Added analyzed_at column to github_repositories")
            else:
                print("analyzed_at column already exists in github_repositories")

            # update analyzed_at column
            cursor.execute(
                "UPDATE github_repositories SET analyzed_at = NOW() WHERE id = %s",
                (analysis_results["id"],),
            )

        connection.commit()

    trigger_self_dag = TriggerDagRunOperator(
        logical_date=(
            pendulum.parse(Variable.get(f"github__api_reset_utc_dt"))
            if Variable.get(f"github__api_reset_utc_dt", None)
            else pendulum.now()
        ),
        task_id="trigger_self_dag",
        trigger_dag_id="analyze_repositories_dag",
    )

    get_repositories() >> analyze() >> update_db() >> trigger_self_dag


analyze_repositories_dag()
