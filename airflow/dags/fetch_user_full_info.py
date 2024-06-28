from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
from airflow.providers.github.operators.github import GithubOperator
from include.github_operator.CustomGithubOperator import CustomGithubOperator
from include.github_operator.utils import result_processor_custom_github_operator


@dag(
    schedule="@once",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    doc_md=__doc__,
    default_args={"owner": "Minki", "retries": 0},
    tags=["github"],
)
def fetch_user_full_info_dag():

    fetch_user_url = CustomGithubOperator(
        if_modified_since="Fri, 28 Jun 2024 00:08:24 GMT",
        task_id="fetch_user_url",
        github_method="get_user",
        github_conn_id="github_default",
        github_method_args={"login": "minki-j"},
        result_processor=lambda res: result_processor_custom_github_operator(res),
        do_xcom_push=True,
    )

    @task()
    def read_user_info(**context):
        user_info, last_modified_datetime = context["ti"].xcom_pull(
            task_ids="fetch_user_url"
        )
        print(f"==>> last_modified_datetime: {last_modified_datetime}")
        print(f"==>> user_info: {user_info}")

    read_user_info_instance = read_user_info()

    fetch_user_url >> read_user_info_instance


fetch_user_full_info_dag()
