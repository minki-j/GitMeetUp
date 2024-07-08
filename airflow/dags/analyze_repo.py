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
from include.utils.generate_tree import generate_tree

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
        repo_pushed_at_threshold = pendulum.now().subtract(days=30).timestamp()

        columns = ["id", "trees_url", "commits_url", "languages_url", "description"]
        columns_str = ", ".join(columns)

        with connection.cursor() as cursor:
            if "analyzed_at" not in existing_columns:
                repo_infos = select_data_with_condition(
                    cursor,
                    table_name="github_repositories",
                    select_condition=columns_str,
                    where_condition=f'TO_TIMESTAMP(pushed_at, \'YYYY-MM-DD"T"HH24:MI:SS"Z"\') > TO_TIMESTAMP({repo_pushed_at_threshold})',
                    limit=batch_size,
                )
            else:
                repo_infos = select_data_with_condition(
                    cursor,
                    table_name="github_repositories",
                    select_condition=columns_str,
                    where_condition=f'TO_TIMESTAMP(pushed_at, \'YYYY-MM-DD"T"HH24:MI:SS"Z"\') > TO_TIMESTAMP({repo_pushed_at_threshold}) AND analyzed_at IS NULL',
                    limit=batch_size,
                )

        if repo_infos is None or len(repo_infos) == 0:
            context["ti"].xcom_push(key="repo_infos", value=[])
            return "end"
        else:
            repo_infos = [dict(zip(columns, repo_info)) for repo_info in repo_infos]
            context["ti"].xcom_push(key="repo_infos", value=repo_infos)
            return "get_last_commit_sha"

    @task()
    def get_last_commit_sha(**context) -> list[dict]:
        print(f"==> Fetching last commit sha")

        repo_infos = context["ti"].xcom_pull(key="repo_infos")

        index = 0
        for index, repo_info in enumerate(repo_infos):
            res = github_api_request(
                "GET",
                repo_info["commits_url"].replace("{/sha}", ""),
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

        context["ti"].xcom_push(key="repo_infos", value=repo_infos)

    @task()
    def get_tree(**context) -> list[dict]:
        print(f"==> Fetching repositories")

        repo_infos = context["ti"].xcom_pull(key="repo_infos")
        print(f"==>> repo_urls: {repo_infos}")

        for idx, repo_info in enumerate(repo_infos):
            response = github_api_request(
                "GET",
                repo_info["trees_url"].replace("{/sha}", "/" + repo_info["last_commit_sha"]),
                last_fetch_at=pendulum.datetime(2024, 1, 1),
                params={"recursive": "true"},
            )
            data = response.json()
            tree = data["tree"]
            repo_infos[idx]["tree"] = generate_tree([item["path"] for item in tree])

        context["ti"].xcom_push(key="repo_infos", value=repo_infos)

    @task()
    def update_db(**context):
        print("==> update_db")
        repo_infos = context["ti"].xcom_pull(key="repo_infos")

        hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
        connection = hook.get_conn()
        with connection.cursor() as cursor:
            create_or_update_table(
                cursor,
                repo_infos,
                table_name="github_repositories",
            )
            insert_data(
                cursor,
                repo_infos,
                table_name="github_repositories",
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
        >> get_last_commit_sha()
        >> get_tree()
        >> update_db()
        >> trigger_analyze_repositories_dag
    )

    get_repo_info_task >> end_task


analyze_repositories_dag()
