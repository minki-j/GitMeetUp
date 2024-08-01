import os

from langchain_core.tools import tool
# from langchain_community.tools.tavily_search import TavilySearchResults


@tool
def read_a_file(path: str):
    """Use this to read a file from the local filesystem."""

    root_path = "/Users/minkijung/Documents/2PetProjects/ernest"
    full_path = os.path.join(root_path, path)
    
    if not os.path.exists(full_path):
        raise ValueError(f"File does not exist at full_path: {full_path}")

    with open(full_path, "r") as f:
        return f.read()

# tavily_search = TavilySearchResults(max_results=2)


tools = [read_a_file]
