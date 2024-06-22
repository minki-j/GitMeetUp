"""
## Scrapping and filtering github accounts and repositories

This DAG is used to scrape and filter github accounts and repositories. The DAG is scheduled to run every hour until it finished scraping all the accounts and repositories in a given location.
"""

from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime
import requests
import os
from dags.utils.fetch_users import fetch_github_acocunts_by_date_location

@dag(
    start_date=datetime(2024, 1, 1),
    schedule="@hourly",
    catchup=False,
    doc_md=__doc__,
    default_args={"owner": "Minki", "retries": 2},
    tags=["github"],
)
def fetch_accounts():
    @task(outlets=[Dataset("github_accounts")])
    def get_accounts(**context) -> list[dict]:
        print("==> get_accounts")
        """
        This task uses the requests library to retrieve a list of Github accounts
        in a given location. The results are pushed to XCom with a specific key
        so they can be used in a downstream pipeline. The task returns a list
        of Github accounts to be used in the next task.
        """
        location = "montreal"
        date = "2024-01-01..2024-01-02"

        accounts, log, rate_limit = fetch_github_acocunts_by_date_location(location, date)
        print(f"Rate limit remaining: {rate_limit}")
        return accounts

    @task
    def print_accounts(accounts: list[dict]) -> None:
        """
        This task prints the name of each Github account in the list of accounts
        from the previous task.
        """
        print("%" * 30)
        for account in accounts:
            print(account["login"])
        print("%" * 30)

    print_accounts.expand(accounts=get_accounts())


fetch_accounts()
