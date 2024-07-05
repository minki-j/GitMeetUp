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

    get_column_names_for_repo = PythonOperator(
        task_id="get_column_names_for_repo",
        python_callable=get_col_names,
        op_args=["github_repositories"],
    )

    get_column_names_for_accounts = PythonOperator(
        task_id="get_column_names_for_accounts",
        python_callable=get_col_names,
        op_args=["github_accounts"],
    )

    @task()
    def get_repo_urls(**context) -> list[dict]:
        hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
        connection = hook.get_conn()
        batch_size = 10
        existing_columns = context["ti"].xcom_pull(task_ids="get_column_names_for_repo")

        with connection.cursor() as cursor:
            if "repos_json" in existing_columns:
                query = f"SELECT id, repos_url FROM github_accounts LIMIT {batch_size}"
                try:
                    cursor.execute(query)
                except Exception as e:
                    print(f"Failed to execute query: {query} / {e}")
                repo_urls = cursor.fetchall()
            else:
                repo_urls = select_data_with_condition(
                    cursor,
                    table_name="github_accounts",
                    select_condition="id, repos_url",
                    where_condition="repos_url IS NOT NULL",
                    limit=batch_size,
                )
        print("repo_urls: ", repo_urls)

        if len(repo_urls) == 0:
            Variable.set("is_fetch_repositories_done", "True")

        return repo_urls

    @task()
    def fetch_repo_urls(**context):
        print(f"==> Fetching repositories")

        repo_urls = context["ti"].xcom_pull(task_ids="get_repo_urls")
        if len(repo_urls) == 0:
            print("No repo_urls to fetch")
            return
        result = []
        index = 0

        for id, url in repo_urls:
            response = github_api_request(
                "GET", url, None, {}
            )  # TODO: Add last_fetched_at
            if response.status_code == 200:
                repositories = response.json()
                last_fetched_at = pendulum.now().to_datetime_string()
                for repo in repositories:
                    # remove unnecessary items from the dict repo_info
                    owner_dict = repo.pop("owner", None)
                    repo["user_id"] = owner_dict["id"]
                    repo["user_login"] = owner_dict["login"]
                    repo["last_fetched_at"] = last_fetched_at
                    # remove nested dict items
                    keys_to_remove = [
                        key for key in repo.keys() if isinstance(repo[key], dict)
                    ]
                    for key in keys_to_remove:
                        value = repo.pop(key)
                        print("Excluded nested item. Key/value:\n", key, " / ", value)

                # print("rate limit: ", response.headers["X-RateLimit-Remaining"])
                # print(
                #     f"reset time(Montreal): {pendulum.from_timestamp(int(response.headers['X-RateLimit-Reset'])).in_tz('America/Montreal')}"
                # )
                if response.headers["X-RateLimit-Remaining"] == 0:
                    print(
                        f"==> 403 Rate limit exceeded. Reset time: {pendulum.from_timestamp(int(response.headers['X-RateLimit-Reset']))}"
                    )
                    Variable.set(
                        "github_api_reset_utc_dt",
                        pendulum.from_timestamp(response.headers["X-RateLimit-Reset"]),
                    )
                    break
            elif response.status_code == 304:
                print(f"==> 304 Not Modified since the last fetch: {url}")
                repositories = {
                    "last_fetched_at": pendulum.now().to_datetime_string(),
                    "id": id,
                }
            elif response.status_code == 403:
                print(f"403 Error for {url} / Message: {response.text}")
                print(
                    f"remaining rate limit: {response.headers['X-RateLimit-Remaining']} reset: {pendulum.from_timestamp(int(response.headers['X-RateLimit-Reset'])).in_tz('America/Montreal')}"
                )
                Variable.set(
                    "github_api_reset_utc_dt",
                    pendulum.from_timestamp(response.headers["X-RateLimit-Reset"]),
                )
                break
            elif response.status_code == 404:
                print(f"Not Found:{url}")
                repositories = {
                    "last_fetched_at": pendulum.now().to_datetime_string(),
                    "id": id,
                }
                # TODO: delete these users from db
            else:
                print(
                    f"{response.status_code} Error for {url} / Message: {response.text}"
                )
            result.extend(repositories)
            index += 1
            if index % 50 == 0:
                print(
                    f"==>> {index} repo fetched / rate limit:  {response.headers['X-RateLimit-Remaining']}"
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
            for id, url in user_infos:
                data.append({"id": id, "repos_last_fetched_at": pendulum.now().to_datetime_string()})
            print("data: ", data)
            update_table_multiple_rows(
                cursor, "github_accounts", column_names_for_accounts, data, "id"
            )
            print("Updated github_accounts")
        connection.commit()

    @task.branch(task_id="is_query_not_completed")
    def is_finished():
        is_finished_str = Variable.get(f"is_fetch_repositories_done", "False")
        is_finished = is_finished_str == "True"

        if is_finished:
            print("==>> Loop is done, branching to end")
            return "end"
        print("==>> Loop is not done, continuing the downstream tasks")
        return "trigger_repositories_dag"

    trigger_filter_accounts_dag = TriggerDagRunOperator(
        start_date=(
            pendulum.datetime(Variable.get(f"github_api_reset_utc_dt", 0), tz="UTC")
            if Variable.get(f"github_api_reset_utc_dt", 0) != 0
            else pendulum.datetime(2024, 1, 1, tz="UTC")
        ),
        task_id="trigger_repositories_dag",
        trigger_dag_id="fetch_repositories_dag",
    )

    end_task = EmptyOperator(task_id="end")

    is_finished_task = is_finished()

    (
        get_column_names_for_repo
        >> get_repo_urls()
        >> fetch_repo_urls()
        >> get_column_names_for_accounts
        >> update_db()
        >> is_finished_task
        >> [trigger_filter_accounts_dag, end_task]
    )


fetch_repositories_dag()
