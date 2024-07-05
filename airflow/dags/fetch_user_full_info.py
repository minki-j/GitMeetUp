import time
import pendulum

from airflow.decorators import dag, task
from airflow.models import Variable

from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from airflow.providers.postgres.hooks.postgres import PostgresHook

from include.github_api_call.request import github_api_request
from dags.common_tasks.get_column_names import get_col_names
from dags.utils.sql import select_data_with_condition, update_table_multiple_rows


@dag(
    schedule="@once",
    start_date=pendulum.datetime(2024, 1, 1, tz="America/Toronto"),
    catchup=False,
    doc_md=__doc__,
    default_args={"owner": "Minki", "retries": 0},
    tags=["github"],
    template_searchpath=Variable.get("TEMPLATE_SEARCHPATH"),
)
def fetch_user_full_info_dag():

    get_column_names = PythonOperator(
        task_id="get_column_names",
        python_callable=get_col_names,
        op_args=["github_accounts"],
    )

    @task()
    def get_urls(**context):
        batch_size = 100
        hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
        connection = hook.get_conn()

        existing_columns = context["ti"].xcom_pull(task_ids="get_column_names")

        with connection.cursor() as cursor:
            if "last_fetched_at" in existing_columns:
                print("==> last_fetched_at exists")
                query = f"SELECT id, url, NULL FROM github_accounts WHERE last_fetched_at IS NULL LIMIT {batch_size}"
                try:
                    cursor.execute(query)
                except Exception as e:
                    print(f"Failed to execute query: {query} / {e}")
                account_infos = cursor.fetchall()
            else:
                account_infos = select_data_with_condition(
                    cursor,
                    table_name="github_accounts",
                    select_condition="id, url, NULL",
                    where_condition=None,
                    limit=batch_size,
                )

        if len(account_infos) == 0:
            Variable.set("is_fetch_user_full_info_done", "True")
        else:
            Variable.set("is_fetch_user_full_info_done", "False")
        return account_infos

    @task()
    def fetch_user_url(account_infos, **context):
        user_info = []
        index = 0
        for id, url, last_fetched_at in account_infos:
            response = github_api_request("GET", url, last_fetched_at, {})
            if response.status_code == 200:
                updated_user_info = response.json()
                updated_user_info["last_fetched_at"] = (
                    pendulum.now().to_datetime_string()
                )

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
                updated_user_info = {"last_fetched_at": pendulum.now().to_datetime_string(), "id": id}
            elif response.status_code == 403:
                print(
                    f"403 Error for {url} / Message: {response.text}"
                )
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
                updated_user_info = {"last_fetched_at": pendulum.now().to_datetime_string(), "id": id}
                # TODO: delete these users from db
            else:
                print(
                    f"{response.status_code} Error for {url} / Message: {response.text}"
                )
            user_info.append(updated_user_info)
            index += 1
            if index % 50 == 0:
                print(f"==>> {index} users fetched / rate limit:  {response.headers['X-RateLimit-Remaining']}")

        return user_info

    @task()
    def update_db(**context):
        print("==> update_db")
        existing_columns = context["ti"].xcom_pull(task_ids="get_column_names")
        user_info = context["ti"].xcom_pull(task_ids="fetch_user_url")
        hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
        connection = hook.get_conn()
        with connection.cursor() as cursor:
            update_table_multiple_rows(
                cursor, "github_accounts", existing_columns, user_info, "id"
            )
        connection.commit()

    @task.branch(task_id="is_query_not_completed")
    def is_finished():
        is_finished_str = Variable.get(f"is_fetch_user_full_info_done", "False")
        is_finished = is_finished_str == "True"

        if is_finished:
            print("==>> Filter is done, branching to end")
            return "end"
        print("==>> Filter is not done, continuing the downstream tasks")
        return "trigger_filter_accounts_dag"

    trigger_filter_accounts_dag = TriggerDagRunOperator(
        start_date=(
            pendulum.datetime(Variable.get(f"github_api_reset_utc_dt", 0), tz="UTC")
            if Variable.get(f"github_api_reset_utc_dt", 0) != 0
            else pendulum.datetime(2024, 1, 1, tz="UTC")
        ),
        task_id="trigger_filter_accounts_dag",
        trigger_dag_id="fetch_user_full_info_dag",
    )

    end_task = EmptyOperator(task_id="end")

    fetch_unprocessed_user_urls_task = get_urls()
    fetch_user_url_task = fetch_user_url(fetch_unprocessed_user_urls_task)
    update_db_task = update_db()
    is_finished_task = is_finished()


    (
        get_column_names
        >> fetch_unprocessed_user_urls_task
        >> fetch_user_url_task
        >> update_db_task
        >> is_finished_task
        >> [trigger_filter_accounts_dag, end_task]
    )



fetch_user_full_info_dag()
