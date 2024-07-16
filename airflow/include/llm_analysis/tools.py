import os

from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults


@tool
def read_a_file(path: str):
    """Use this to read a file from the local filesystem."""

    if not os.path.exists(path):
        raise ValueError(f"File does not exist at path: {path}")

    with open(path, "r") as f:
        return f.read()

tavily_search = TavilySearchResults(max_results=2)


tools = [read_a_file, tavily_search]
