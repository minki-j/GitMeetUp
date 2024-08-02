import os
from ..state_schema import State
import json


def read_files_suggested_by_LLM(state: State):

    root_path = state["repo_root_path"]
    valid_paths = state["valid_paths"]

    opened_files = {}
    for full_path in valid_paths:
        # pass jupyter notebook files
        if full_path.endswith(".ipynb"):
            print(f"Skipping jupyter notebook file: {full_path}")
            continue
        if not os.path.exists(full_path):
            raise ValueError(f"File does not exist at full_path: {full_path}")

        with open(full_path, "r") as f:
            opened_files[full_path.replace(root_path, "")] = f.read()

    return {"opened_files": opened_files}
