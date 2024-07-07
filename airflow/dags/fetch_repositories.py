"""
### Github Repo DAG
This DAG is used to scrape repositories from Github acocunts. The DAG is scheduled to run whenever the `github_accounts` dataset is updated.
"""

import time
import pendulum

from airflow.decorators import dag, task
from airflow.models import Variable


from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from airflow.providers.postgres.hooks.postgres import PostgresHook

from dags.common_tasks.get_column_names import get_col_names
from dags.utils.sql import (
    select_data_with_condition,
    update_table_multiple_rows,
    create_or_update_table,
    insert_data,
)
from include.github_api_call.request import github_api_request


@dag(
    schedule="@once",
    start_date=pendulum.datetime(2024, 1, 1, tz="America/Montreal"),
    catchup=False,
    doc_md=__doc__,
    default_args={"owner": "Minki", "retries": 0},
    tags=["github"],
)
def fetch_repositories_dag():

    get_column_names_for_accounts = PythonOperator(
        task_id="get_column_names_for_accounts",
        python_callable=get_col_names,
        op_args=["github_accounts"],
    )

    @task()
    def get_repo_urls(**context) -> list[dict]:
        hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
        connection = hook.get_conn()
        batch_size = 100

        with connection.cursor() as cursor:
            repo_urls = select_data_with_condition(
                cursor,
                table_name="github_accounts",
                select_condition="id, repos_url",
                where_condition="repos_url IS NOT NULL AND repos_last_fetched_at IS NULL",
                limit=batch_size,
            )
        print("repo_urls: ", repo_urls)

        if len(repo_urls) == 0:
            Variable.set("is_fetch_repositories_done", "True")
        else:
            Variable.set("is_fetch_repositories_done", "False")

        return repo_urls

    @task()
    def fetch_repo_urls(**context) -> list[dict]:
        print(f"==> Fetching repositories")

        repo_urls = context["ti"].xcom_pull(task_ids="get_repo_urls")
        if len(repo_urls) == 0:
            print("No repo_urls to fetch")
            return
        result = []
        index = 0

        for user_id, url in repo_urls:
            res = github_api_request("GET", url, None)  # TODO: Add last_fetched_at
            if res.status_code == 200:
                repositories = res.json()
                if len(repositories) == 0:
                    continue

                for repo in repositories:
                    # remove unnecessary items from the dict repo_info
                    repo.pop("owner", None)

                    # remove nested dict items
                    nested_items_key = [
                        key for key in repo.keys() if isinstance(repo[key], dict)
                    ]
                    for key in nested_items_key:
                        value = repo.pop(key)
                        # print("Excluded nested item. Key/value:\n", key, " / ", value)
            else:
                repositories = [{}]

            for repo in repositories:
                repo["user_id"] = user_id
                repo["last_fetched_at"] = pendulum.now().to_datetime_string()

            if res.headers["X-RateLimit-Remaining"] == 0:
                print(
                    f"==> 403 Rate limit exceeded. Reset time: {pendulum.from_timestamp(int(res.headers['X-RateLimit-Reset']))}"
                )
                Variable.set(
                    "github_api_reset_utc_dt",
                    pendulum.from_timestamp(int(res.headers["X-RateLimit-Reset"])),
                )
                break
            else:
                Variable.delete("github_api_reset_utc_dt")

            result.extend(repositories)
            index += 1
            if index % 50 == 0:
                print(
                    f"==>> {index} repo fetched / rate limit:  {res.headers['X-RateLimit-Remaining']}"
                )

        print("Total ", len(result), " repositories fetched")

        return result

    @task()
    def update_db(**context):
        print("==> update_db")
        column_names_for_accounts = context["ti"].xcom_pull(
            task_ids="get_column_names_for_accounts"
        )
        user_infos = context["ti"].xcom_pull(task_ids="get_repo_urls")
        repositories = context["ti"].xcom_pull(task_ids="fetch_repo_urls")

        hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
        connection = hook.get_conn()
        with connection.cursor() as cursor:
            create_or_update_table(
                cursor,
                repositories,
                table_name="github_repositories",
            )
            insert_data(
                cursor,
                repositories,
                table_name="github_repositories",
            )

            # mark the repo_last_fetch_at in github_accounts
            data = []
            for id, _ in user_infos:
                data.append(
                    {
                        "id": id,
                        "repos_last_fetched_at": pendulum.now().to_datetime_string(),
                    }
                )
            update_table_multiple_rows(
                cursor, "github_accounts", column_names_for_accounts, data, "id"
            )
        connection.commit()

    @task.branch(task_id="is_query_not_completed")
    def is_finished():
        is_finished_str = Variable.get(f"is_fetch_repositories_done", "False")
        is_finished = is_finished_str == "True"

        if is_finished:
            print("==>> Loop is done, branching to end")
            return "end"
        print("==>> Loop is not done, continuing the downstream tasks")
        return "trigger_fetch_repositories_dag"

    trigger_filter_accounts_dag = TriggerDagRunOperator(
        logical_date=(
            Variable.get(f"github_api_reset_utc_dt", 0)
            if Variable.get(f"github_api_reset_utc_dt", 0) != 0
            else pendulum.now(tz="UTC").to_datetime_string()
        ),
        task_id="trigger_fetch_repositories_dag",
        trigger_dag_id="fetch_repositories_dag",
    )

    end_task = EmptyOperator(task_id="end")

    is_finished_task = is_finished()

    (
        get_repo_urls()
        >> fetch_repo_urls()
        >> get_column_names_for_accounts
        >> update_db()
        >> is_finished_task
        >> trigger_filter_accounts_dag
    )

    is_finished_task >> end_task


fetch_repositories_dag()
