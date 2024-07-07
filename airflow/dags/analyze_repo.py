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

# TODO: languages, description, recent_30_commits, pushed_at, packages_used, directory_structure
#
# llm_inspection_for_commits
# llm_inspection_for_entire_repo


@dag(
    schedule="@once",
    start_date=pendulum.datetime(2024, 1, 1, tz="America/Montreal"),
    catchup=False,
    doc_md=__doc__,
    default_args={"owner": "Minki", "retries": 0},
    tags=["github"],
)
def analyze_repositories_dag():

    get_column_names_for_repositories = PythonOperator(
        task_id="get_column_names_for_repositories",
        python_callable=get_col_names,
        op_args=["github_repositories"],
    )

    @task.branch()
    def get_repo_info(**context) -> list[dict]:
        existing_columns = context["ti"].xcom_pull(
            task_ids="get_column_names_for_repositories"
        )

        hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
        connection = hook.get_conn()
        batch_size = 2
        repo_pushed_at_threshold = pendulum.now().subtract(days=30).to_datetime_string()

        with connection.cursor() as cursor:
            if "analyzed_at" not in existing_columns:
                repo_urls = select_data_with_condition(
                    cursor,
                    table_name="github_repositories",
                    select_condition="id, trees_url, commits_url, languages_url, description",
                    where_condition=f"pushed_at > {repo_pushed_at_threshold}",
                    limit=batch_size,
                )
            else:
                repo_urls = select_data_with_condition(
                    cursor,
                    table_name="github_repositories",
                    select_condition="id, trees_url, commits_url, languages_url, description",
                    where_condition=f"pushed_at > {repo_pushed_at_threshold} AND analyzed_at IS NULL",
                    limit=batch_size,
                )
        print("repo_urls: ", repo_urls)

        if len(repo_urls) == 0:
            context["ti"].xcom_push(key="repo_infos", value=[])
            return "end"
        else:
            context["ti"].xcom_push(key="repo_infos", value=repo_urls)
            return "get_tree"

    @task()
    def get_last_commit_sha(**context) -> list[dict]:
        print(f"==> Fetching last commit sha")

        repo_infos = context["ti"].xcom_pull(task_ids="repo_infos")

        result = []
        index = 0
        for index, (id, trees_url, commits_url, languages_url, description) in enumerate(repo_infos):
            res = github_api_request(
                "GET",
                commits_url.replace("{/sha}", ""),
                last_fetch_at=pendulum.datetime(2024, 1, 1),
                params={"recursive": "true"},
            )
            commits = res.json()
            if len(commits) == 0:
                continue
            print(commits[0])
            repo_infos[index]["last_commit_sha"] = commits[0]["sha"]
                
            if res.headers["X-RateLimit-Remaining"] == 0:
                print(
                    f"==> 403 Rate limit exceeded. Reset time: {pendulum.from_timestamp(int(res.headers['X-RateLimit-Reset']))}"
                )
                Variable.set(
                    "github_api_reset_utc_dt",
                    pendulum.from_timestamp(
                        int(res.headers["X-RateLimit-Reset"])
                    ),
                )
                break
            else:
                Variable.delete("github_api_reset_utc_dt")
            

            index += 1
            if index % 50 == 0 or index == len(repo_infos) - 1:
                print(
                    f"==>> {index} commit sha fetched / rate limit:  {res.headers['X-RateLimit-Remaining']}"
                )

    @task()
    def get_tree(**context) -> list[dict]:
        print(f"==> Fetching repositories")

        repo_urls = context["ti"].xcom_pull(task_ids="repo_infos")

        result = []
        index = 0
        response = github_api_request(
            "GET",
            "https://api.github.com/repos/minki-j/gitmeetup/git/trees/ee85e2c53e0c97c523df2016e6488440fd324a55",
            last_fetch_at=pendulum.datetime(2024, 1, 1),
            params={"recursive": "true"},
        )

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

    trigger_analyze_repositories_dag = TriggerDagRunOperator(
        logical_date=(
            Variable.get(f"github_api_reset_utc_dt", 0)
            if Variable.get(f"github_api_reset_utc_dt", 0) != 0
            else pendulum.now(tz="UTC").to_datetime_string()
        ),
        task_id="trigger_analyze_repositories_dag",
        trigger_dag_id="analyze_repositories_dag",
    )

    end_task = EmptyOperator(task_id="end")

    get_repo_info_task = get_repo_info()

    (
        get_column_names_for_repositories
        >> get_repo_info_task
        >> get_tree()
        >> update_db()
        >> trigger_analyze_repositories_dag
    )

    get_repo_info_task >> end_task


analyze_repositories_dag()
