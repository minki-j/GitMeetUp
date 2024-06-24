"""
### Github Repo DAG
This DAG is used to scrape repositories from Github acocunts. The DAG is scheduled to run whenever the `github_accounts` dataset is updated.
"""

from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime


@dag(
    schedule="@once",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    doc_md=__doc__,
    default_args={"owner": "Minki", "retries": 2},
    tags=["github"],
)
def fetch_repositories():
    @task(outlets=[Dataset("github_repositories")])
    def get_accounts(**context) -> list[dict]:
        print("==> get_repositories")
        """
        This task uses the requests library to retrieve a list of Github repositories
        for a given account. The results are pushed to XCom with a specific key
        so they can be used in a downstream pipeline. The task returns a list
        of Github repositories to be used in the next task.
        """
        accounts = context["ti"].xcom_pull(
            dag_id="fetch_accounts",
            task_ids="get_accounts",
            key="accounts",
            include_prior_dates=True,
        )

        print(f"==>> accounts: {accounts}")
        return accounts

    @task
    def print_repositories(accounts: list[dict]) -> None:
        """
        This task prints the name of each Github repository in the list of repositories
        from the previous task.
        """
        print("%" * 30)
        for account in accounts:
            print(account["login"])
        print("%" * 30)

    print_repositories(accounts=get_accounts())


fetch_repositories()
