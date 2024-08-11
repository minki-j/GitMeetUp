"""
### Github Repo DAG
This DAG is used to scrape repositories from Github acocunts. The DAG is scheduled to run whenever the `github_accounts` dataset is updated.
"""
import pendulum

from airflow.decorators import dag, task
from airflow.models import Variable

from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from airflow.providers.postgres.hooks.postgres import PostgresHook

from dags.common_tasks.get_column_names import get_col_names
from include.utils.sql_functions import (
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

    @task.branch()
    def get_repo_urls(**context) -> list[dict]:
        hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
        connection = hook.get_conn()
        batch_size = 100

        existing_cols = context["ti"].xcom_pull(
            task_ids="get_column_names_for_accounts"
        )

        with connection.cursor() as cursor:
            repo_urls = select_data_with_condition(
                cursor,
                table_name="github_accounts",
                select_condition="id, repos_url",
                where_condition=f"repos_url IS NOT NULL {'AND repos_last_fetched_at IS NULL' if 'repos_last_fetched_at' in existing_cols else ''}",
                limit=batch_size,
            )
        print("repo_urls: ", repo_urls)

        if len(repo_urls) == 0:
            print("==>> Loop is done, trigger the next dag")
            return "trigger_fetch_full_repositories_dag"
        else:
            print("==>> Loop is not done, keep running the downstream tasks")
            context["ti"].xcom_push(key="repo_urls", value=repo_urls)
            return "fetch_repo_urls"

    @task()
    def fetch_repo_urls(**context) -> list[dict]:
        print(f"==> Fetching repositories")

        repo_urls = context["ti"].xcom_pull(key="repo_urls")

        result = []
        index = 0
        for user_id, url in repo_urls:
            res = github_api_request("GET", url, None)  # TODO: Add last_fetched_at
            if res.status_code == 200:
                repositories = res.json()
                if len(repositories) == 0:
                    index += 1
                    if index % 50 == 0 or index == len(repo_urls):
                        print(
                            f"==>> {index} repo fetched / rate limit:  {res.headers['X-RateLimit-Remaining']}"
                        )
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
                print(f"==> Failed to fetch repositories: {url}")
                continue

            for repo in repositories:
                repo["user_id"] = user_id
                repo["last_fetched_at"] = pendulum.now().to_datetime_string()

            if int(res.headers["X-RateLimit-Remaining"]) == 0:
                print(
                    f"==> 403 Rate limit exceeded. Reset time UTC: {pendulum.from_timestamp(int(res.headers['X-RateLimit-Reset']))}"
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
            if index % 50 == 0 or index == len(repo_urls):
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
        repo_urls = context["ti"].xcom_pull(key="repo_urls")
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
            for id, _repo_url in repo_urls:
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

    trigger_self_dag = TriggerDagRunOperator(
        logical_date=(
            pendulum.parse(Variable.get(f"github_api_reset_utc_dt"))
            if Variable.get(f"github_api_reset_utc_dt", None)
            else pendulum.now()
        ),
        task_id="trigger_self_dag",
        trigger_dag_id="fetch_repositories_dag",
    )

    trigger_fetch_full_repositories_dag = TriggerDagRunOperator(
        logical_date=(
            pendulum.parse(Variable.get(f"github_api_reset_utc_dt"))
            if Variable.get(f"github_api_reset_utc_dt", None)
            else pendulum.now()
        ),
        task_id="trigger_fetch_full_repositories_dag",
        trigger_dag_id="fetch_full_repositories_dag",
    )

    get_repo_urls_task = get_repo_urls()
    (
        get_column_names_for_accounts
        >> get_repo_urls_task
        >> fetch_repo_urls()
        >> update_db()
        >> trigger_self_dag
    )

    get_repo_urls_task >> trigger_fetch_full_repositories_dag


fetch_repositories_dag()
