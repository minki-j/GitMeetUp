import os
import re
import json
import subprocess
import pendulum
import shlex

from airflow.decorators import dag, task
from airflow.models import Variable

from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from airflow.providers.postgres.hooks.postgres import PostgresHook

from dags.common_tasks.get_column_names import get_col_names
from include.utils.sql_functions import (
    select_data_with_condition,
    create_or_update_table,
    insert_data,
    create_document_table,
    insert_document,
)
from include.github_api_call.request import github_api_request
from include.github_api_call.functions import fetch_commits
from include.utils.generate_tree import generate_tree


@dag(
    schedule="@once",
    start_date=pendulum.datetime(2024, 1, 1, tz="America/Montreal"),
    catchup=False,
    doc_md=__doc__,
    default_args={"owner": "Minki", "retries": 0},
    tags=["github"],
)
def fetch_full_repositories_dag():

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
        batch_size = 100
        repo_pushed_at_threshold = pendulum.now().subtract(days=30).timestamp()

        columns = [
            "id",
            "full_name",
            "trees_url",
            "commits_url",
            "languages_url",
            "description",
            "clone_url",
            "fork",
        ]
        columns_str = ", ".join(columns)

        with connection.cursor() as cursor:
            where_condition = f"""
            TO_TIMESTAMP(pushed_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') > TO_TIMESTAMP({repo_pushed_at_threshold})
            AND TO_TIMESTAMP(pushed_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') > TO_TIMESTAMP(created_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') + interval '1 day'
            AND size < 50000
            """ + (
                "AND fetched_full_info_at IS NULL"
                if "fetched_full_info_at" in existing_columns
                else ""
            )

            repo_infos = select_data_with_condition(
                cursor,
                table_name="github_repositories",
                select_condition=columns_str,
                where_condition=where_condition,
                limit=batch_size,
            )

        if repo_infos is None or len(repo_infos) == 0:
            context["ti"].xcom_push(key="repo_infos", value=[])
            return "end"
        else:
            repo_infos = [dict(zip(columns, repo_info)) for repo_info in repo_infos]
            context["ti"].xcom_push(key="repo_infos", value=repo_infos)
            return "get_commit_sha"

    @task()
    def get_commit_sha(**context) -> list[dict]:
        print(f"==> Fetching last commit sha")
        existing_columns = context["ti"].xcom_pull(
            task_ids="get_column_names_for_repositories"
        )
        repo_infos = context["ti"].xcom_pull(key="repo_infos")
        # Manually fetch repositories
        # repo_infos = [{
        #     "commits_url": "https://api.github.com/repos/minki-j/GitMeetUp/commits{/sha}",
        #     "id": 816994095,
        #     "full_name": "minki-j/GitMeetUp",
        # }]

        index = 0
        hook = PostgresHook(postgres_conn_id=Variable.get("POSTGRES_CONN_ID"))
        connection = hook.get_conn()
        with connection.cursor() as cursor:
            for index, repo_info in enumerate(repo_infos):
                (
                    commits,
                    is_overflowed,
                    reached_rate_limit,
                    remaining_rate_limit,
                    rate_limit_reset_time,
                ) = fetch_commits(
                    repo_info["commits_url"].replace("{/sha}", ""),
                    params={"per_page": 100},
                )
                if is_overflowed:
                    print(f"==> More then 1000 commits in {repo_info['full_name']}")

                if reached_rate_limit:
                    print(
                        f"==> 403 Rate limit exceeded. Reset time UTC: {rate_limit_reset_time}"
                    )
                    Variable.set("github_api_reset_utc_dt", rate_limit_reset_time)
                    break
                else:
                    Variable.delete("github_api_reset_utc_dt")

                if len(commits) == 0:
                    continue
                repo_infos[index]["last_commit_sha"] = commits[0]["sha"]

                commits = [
                    {
                        k: v
                        for k, v in commit.items()
                        if k in ["sha", "commit", "url", "html_url", "comments_url"]
                    }
                    for commit in commits
                ]
                if "fetched_full_info_at" not in existing_columns:
                    create_document_table(cursor, "github_commits")
                insert_document(cursor, "github_commits", repo_info["id"], commits)

                #! REMOVE THIS AFTER FETCHING COMMIT SHA
                if "fetched_full_info_at" not in existing_columns:
                    repo_info["fetched_full_info_at"] = (
                        pendulum.now().to_datetime_string()
                    )
                    create_or_update_table(cursor, [repo_info], "github_repositories")
                insert_data(
                    cursor,
                    [
                        {
                            "id": repo_info["id"],
                            "fetched_full_info_at": pendulum.now().to_datetime_string(),
                        }
                    ],
                    table_name="github_repositories",
                )

                index += 1
                if index % 50 == 0 or index == len(repo_infos):
                    print(
                        f"{index} commits fetched / remaining rate limit:  {remaining_rate_limit}"
                    )

        connection.commit()

        context["ti"].xcom_push(key="repo_infos", value=repo_infos)

    @task()
    def get_tree(**context):
        print(f"==> Fetching repositories")

        repo_infos = context["ti"].xcom_pull(key="repo_infos")
        print(f"==>> repo_infos: {repo_infos}")

        for idx, repo_info in enumerate(repo_infos):
            if (
                "last_commit_sha" not in repo_info
                or repo_info["last_commit_sha"] is None
            ):
                continue
            response = github_api_request(
                "GET",
                repo_info["trees_url"].replace(
                    "{/sha}", "/" + repo_info["last_commit_sha"]
                ),
                last_fetch_at=None,
                params={"recursive": "true"},
            )
            data = response.json()
            tree = data["tree"]
            repo_infos[idx]["tree"] = generate_tree([item["path"] for item in tree])

        context["ti"].xcom_push(key="repo_infos", value=repo_infos)

    @task()
    def get_full_list_of_languages(**context):
        print(f"==> get_full_list_of_languages")

        repo_infos = context["ti"].xcom_pull(key="repo_infos")
        print(f"==>> repo_infos: {repo_infos}")

        for idx, repo_info in enumerate(repo_infos):
            response = github_api_request(
                "GET",
                repo_info["languages_url"],
                last_fetch_at=None,
                params={},
            )
            data = response.json()
            print(f"==>> data: {data}")
            repo_infos[idx]["languages_full_list"] = data

        context["ti"].xcom_push(key="repo_infos", value=repo_infos)

    @task()
    def get_packages_used(**context):
        print(f"==> Fetching repositories")
        languages_to_extract_packages = [
            "Python",
            "JavaScript",
            "TypeScript",
            "Jupyter Notebook",
        ]

        repo_infos = context["ti"].xcom_pull(key="repo_infos")
        for repo_info in repo_infos:
            repo_info["packages_used"] = ""

            if not any(
                language.lower()
                in (key.lower() for key in repo_info["languages_full_list"].keys())
                for language in languages_to_extract_packages
            ):
                continue

            clone_url = repo_info["clone_url"]

            target_dir = os.path.join("./cloned_repositories", repo_info["full_name"])
            requirement_dir = os.path.join("./packages_used", repo_info["full_name"])

            result = subprocess.run(
                "rm -rf " + target_dir,
                capture_output=True,
                check=True,
                text=True,
                shell=True,
            )

            try:
                print("start cloning ", clone_url)
                result = subprocess.run(
                    "git clone " + clone_url + " " + target_dir,
                    capture_output=True,
                    check=True,
                    text=True,
                    shell=True,
                )
            except subprocess.CalledProcessError as e:
                print(f"Error cloning repository: {e}")
                print(f"Return code: {e.returncode}")
                print(f"Output: {e.output}")
                print(f"Error output: {e.stderr}")
                continue

            # create requirement_dir
            result = subprocess.run(
                "mkdir -p " + requirement_dir + " && ls",
                capture_output=True,
                check=True,
                text=True,
                shell=True,
            )

            # Extracing Python packages
            if any(
                language.lower in repo_info["languages_full_list"].keys()
                for language in ["Python", "Jupyter Notebook"]
            ):
                save_path = os.path.join(requirement_dir, "requirements.txt")
                while True:
                    try:
                        result = subprocess.run(
                            "pipreqs --scan-notebooks --mode no-pin --savepath "
                            + save_path
                            + " "
                            + target_dir,
                            capture_output=True,
                            check=True,
                            text=True,
                            shell=True,
                        )

                        # TODO: need to handle jupyter notebook separately since it's not covered by pipreqs

                        with open(save_path, "r") as f:
                            requirements = f.read().splitlines()

                        requirements = [
                            re.sub(r"==.*", "", requirement)
                            for requirement in requirements
                        ]
                        print(f"python packages: {requirements}")

                        repo_info["packages_used"] += ", ".join(requirements)

                        break
                    except subprocess.CalledProcessError as e:
                        result = re.search(r"Failed on file: (.+\.\w+)", e.stderr)
                        if result:
                            error_file_path = result.group(1)
                            error_file_path_quoted = shlex.quote(error_file_path)
                            # print(f"Error on file {error_file_path}")
                            result = subprocess.run(
                                "rm " + error_file_path_quoted,
                                capture_output=True,
                                check=True,
                                text=True,
                                shell=True,
                            )
                            # print(f"removed the file: {result}")
                            continue
                        else:
                            print(
                                f"No error file path found for {clone_url}, which means that the error is not related to the file. Check the error message: {e.stderr}"
                            )
                            break

            # Extracting JavaScript packages
            if any(
                language in repo_info["languages_full_list"].keys()
                for language in ["JavaScript", "TypeScript"]
            ):
                # find package.json file from the repo
                package_json_files = []
                for root, dirs, files in os.walk(target_dir):
                    for file in files:
                        if file == "package.json":
                            package_json_files.append(os.path.join(root, file))

                if len(package_json_files) == 0:
                    continue

                # extract packages from package.json
                packages = []
                for package_json_file in package_json_files:
                    with open(package_json_file, "r") as f:
                        try:
                            package_json = json.load(f)
                            if "dependencies" in package_json:
                                packages.extend(package_json["dependencies"].keys())
                        except json.JSONDecodeError as e:
                            print(f"Error decoding {package_json_file}: {e}")
                            print(f.read())
                            continue
                packages = [package.replace("@", "") for package in packages]
                print("JavaScript packages: ", packages)
                repo_info["packages_used"] += ", ".join(packages)

            # remove cloned repo and requirement dir
            result = subprocess.run(
                "rm -rf " + target_dir + "&& rm -rf " + requirement_dir,
                capture_output=True,
                check=True,
                text=True,
                shell=True,
            )

        context["ti"].xcom_push(key="repo_infos", value=repo_infos)

    @task()
    def update_db(**context):
        print("==> update_db")
        repo_infos = context["ti"].xcom_pull(key="repo_infos")

        for repo_info in repo_infos:
            repo_info["fetched_full_info_at"] = pendulum.now().to_datetime_string()

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

    # trigger_self_dag = TriggerDagRunOperator(
    #     logical_date=(
    #         pendulum.parse(Variable.get(f"github__api_reset_utc_dt"))
    #         if Variable.get(f"github__api_reset_utc_dt", None)
    #         else pendulum.now()
    #     ),
    #     task_id="trigger_self_dag",
    #     trigger_dag_id="fetch_full_repositories_dag",
    # )

    end_task = EmptyOperator(task_id="end")

    get_repo_info_task = get_repo_info()

    (
        get_column_names_for_repositories
        >> get_repo_info_task
        >> get_commit_sha()
        # >> get_tree()
        # >> get_full_list_of_languages()
        # >> get_packages_used()
        # >> update_db()
        # >> trigger_self_dag
    )

    get_repo_info_task >> end_task


fetch_full_repositories_dag()
