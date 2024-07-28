from typing import Annotated, TypedDict, List, Sequence
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class State(TypedDict):
    @staticmethod
    def merge_lists(attribute_instance: List, new_result: List) -> List:
        for item in new_result:
            if item not in attribute_instance:
                attribute_instance.append(item)
        return attribute_instance

    title: str
    repo_root_path: str
    repo_description_by_user: str
    directory_tree: str
    packages_used: List[str]

    messages: Annotated[Sequence[BaseMessage], add_messages]

    opened_files: dict[str, str] = {}

    invalid_paths: List[str] = []
    valid_paths: Annotated[List[str], merge_lists] = []
    corrected_paths: List[str] = []
    validate_count: int = 0

    analysis_results: Annotated[List[dict], merge_lists] = []
    final_hypotheses: Annotated[List[str], merge_lists] = []

    retrieved_code_snippets: str

    def __init__(self):
        self.analysis_results = []
        self.valid_paths = []
        self.corrected_paths = []
        self.invalid_paths = []
