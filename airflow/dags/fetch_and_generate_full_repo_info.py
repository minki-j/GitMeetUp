import pendulum
import subprocess
import os
import re
import json

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
        batch_size = 10
        repo_pushed_at_threshold = pendulum.now().subtract(days=30).timestamp()

        columns = [
            "id",
            "full_name",
            "trees_url",
            "commits_url",
            "languages_url",
            "description",
            "clone_url",
        ]
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
                last_fetch_at=None, # TODO: Add last_fetched_at
                params={"recursive": "true"},
            )
            if res.status_code != 200:
                continue
            commits = res.json()
            if len(commits) == 0:
                continue
            print(commits[0])
            repo_infos[index]["last_commit_sha"] = commits[0]["sha"]

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

            index += 1
            if index % 50 == 0 or index == len(repo_infos) - 1:
                print(
                    f"==>> {index} commit sha fetched / rate limit:  {res.headers['X-RateLimit-Remaining']}"
                )

        context["ti"].xcom_push(key="repo_infos", value=repo_infos)

    @task()
    def get_tree(**context):
        print(f"==> Fetching repositories")

        repo_infos = context["ti"].xcom_pull(key="repo_infos")
        print(f"==>> repo_infos: {repo_infos}")

        for idx, repo_info in enumerate(repo_infos):
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
            # if the languages of the porject is not in the languages_to_extract_packages, skip the project
            repo_info["packages_used"] = ""
            if not any(
                language.lower() in (key.lower() for key in repo_info["languages_full_list"].keys())
                for language in languages_to_extract_packages
            ):
                continue
            clone_url = repo_info["clone_url"]
            print(f"==>> clone_url: {clone_url}")
            target_dir = os.path.join("./cloned_repositories", repo_info["full_name"])
            print(f"==>> target_dir: {target_dir}")
            requirement_dir = os.path.join("./packages_used", repo_info["full_name"])
            print(f"==>> requirement_dir: {requirement_dir}")

            result = subprocess.run(
                "ls",
                capture_output=True,
                check=True,
                text=True,
                shell=True,
            )
            print("current dir: ", result)

            result = subprocess.run(
                "rm -rf " + target_dir,
                capture_output=True,
                check=True,
                text=True,
                shell=True,
            )
            print(f"remove directory {target_dir}")

            try:
                result = subprocess.run(
                    "git clone " + clone_url + " " + target_dir,
                    capture_output=True,
                    check=True,
                    text=True,
                    shell=True,
                )
                print("git clone result: ", result)
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
            print("create requirement dir: ", result)

            # Extracing Python packages
            if "Python" in repo_info["languages_full_list"].keys():
                save_path = os.path.join(requirement_dir, "requirements.txt")
                exlude_dirs = []
                while True:
                    try:
                        result = subprocess.run(
                            "pipreqs --savepath "
                            + save_path
                            # + " --ignore "
                            # + ",".join(exlude_dirs)
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
                            print(f"==>> requirements: {requirements}")

                        repo_info["packages_used"] += requirements

                        break
                    except subprocess.CalledProcessError as e:
                        error_msg = e.stderr
                        error_file_path = re.search(
                            r"Failed on file: (.+\.\w+)", error_msg
                        ).group(1)
                        if not error_file_path:

                            print(
                                f"No error file path found for {clone_url}, which means that the error is not related to the file. Check the error message: {error_msg}"
                            )
                            break
                        else:
                            exlude_dirs.append(error_file_path)
                            print(f"Error on file {error_file_path}")
                            result = subprocess.run(
                                "rm " + error_file_path,
                                capture_output=True,
                                check=True,
                                text=True,
                                shell=True,
                            )
                            print(f"remove the file: {result}")
                            continue

            if any(["JavaScript", "TypeScript"] in repo_info["languages_full_list"].keys()):
                print("==>> JavaScript or TypeScript")
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
                        package_json = json.load(f)
                        if "dependencies" in package_json:
                            packages.extend(package_json["dependencies"].keys())

                repo_info["packages_used"] += ", ".join(packages)

            result = subprocess.run(
                "rm -rf " + target_dir,
                capture_output=True,
                check=True,
                text=True,
                shell=True,
            )
            print(f"remove cloned repo {target_dir}: {result}")

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

    # trigger_analyze_repositories_dag = TriggerDagRunOperator(
    #     logical_date=(
    #         pendulum.parse(Variable.get(f"github__api_reset_utc_dt"))
    #         if Variable.get(f"github__api_reset_utc_dt", None)
    #         else pendulum.now()
    #     ),
    #     task_id="trigger_analyze_repositories_dag",
    #     trigger_dag_id="analyze_repositories_dag",
    # )

    end_task = EmptyOperator(task_id="end")

    get_repo_info_task = get_repo_info()

    (
        get_column_names_for_repositories
        >> get_repo_info_task
        >> get_last_commit_sha()
        >> get_tree()
        >> get_full_list_of_languages()
        >> get_packages_used()
        >> update_db()
        >> end_task
    )

    get_repo_info_task >> end_task


analyze_repositories_dag()
