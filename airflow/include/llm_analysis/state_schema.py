from typing import Annotated, TypedDict, List, Sequence
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class State(TypedDict):

    @staticmethod
    def append_list(
        attribute_instance: List[dict], new_result: List[dict]
    ) -> List[dict]:
        attribute_instance.extend(new_result)

        return attribute_instance

    title: str
    repo_root_path: str
    repo_description: str
    directory_tree: str
    packages_used: List[str]
    steps: Annotated[List[str], append_list]
    analysis_results: Annotated[List[dict], append_list]
    messages: Annotated[Sequence[BaseMessage], add_messages]
    read_file: str
