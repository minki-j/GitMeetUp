# dags/example_modal_operator.py

"""
## ModalOperator + Sandboxes example

"""

from airflow.decorators import dag
from include.modal_operator import ModalOperator
from dags.utils.scripts import fetch_reddit
from datetime import datetime
import modal
import os


@dag(
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    doc_md=__doc__,
    tags=["example"],
)
def example_modal_operator():
    print("MODAL_TOKEN_ID: ", os.environ["MODAL_TOKEN_ID"])
    print("MODAL_TOKEN_SECRET: ", os.environ["MODAL_TOKEN_SECRET"])
    reddit = ModalOperator(
        task_id="fetch_reddit",
        # pass in your Modal token credentials from environment variables
        client=modal.Client.from_credentials(
            token_id=os.environ["MODAL_TOKEN_ID"],
            token_secret=os.environ["MODAL_TOKEN_SECRET"],
        ),
        # function we import from `scripts.py`
        fn=fetch_reddit,
        sandbox_config={
            # define Python dependencies
            "image": modal.Image.debian_slim().pip_install("praw"),
            # attach Modal secret containing our Reddit API credentials
            "secrets": [modal.Secret.from_name("reddit-secret")],
            # attach Volume, where the output of the script will be stored
            "volumes": {"/data": modal.Volume.from_name("airflow-sandbox-vol")},
        },
    )

    reddit


# instantiate the DAG
example_modal_operator()
