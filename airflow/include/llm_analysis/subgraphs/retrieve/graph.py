from varname import nameof as n

from langgraph.graph import END, StateGraph
from langchain_core.runnables import RunnablePassthrough

from ...utils.converters import to_path_map
from ...state_schema import State

from ...nodes.read_files import read_files_suggested_by_LLM
from ...nodes.file_path_validation import (
    validate_file_paths_from_LLM,
    correct_file_paths,
)
from ...nodes.retrieve_code_snippets import retrieve_code_by_hybrid_search_with_queries

g = StateGraph(State)
g.add_node("entry", RunnablePassthrough())
g.set_entry_point("entry")
g.add_edge("entry", n(retrieve_code_by_hybrid_search_with_queries))
g.add_edge("entry", n(validate_file_paths_from_LLM))

g.add_node(
    n(retrieve_code_by_hybrid_search_with_queries),
    retrieve_code_by_hybrid_search_with_queries,
)
g.add_edge(n(retrieve_code_by_hybrid_search_with_queries), END)

g.add_node(n(validate_file_paths_from_LLM), validate_file_paths_from_LLM)
g.add_conditional_edges(
    n(validate_file_paths_from_LLM),
    lambda state: (
        n(correct_file_paths)
        if len(state["invalid_paths"]) > 0 and state["validate_count"] < 3
        else n(read_files_suggested_by_LLM)
    ),
    to_path_map(
        [
            n(correct_file_paths),
            n(read_files_suggested_by_LLM),
        ]
    ),
)

g.add_node(n(correct_file_paths), correct_file_paths)
g.add_edge(n(correct_file_paths), n(validate_file_paths_from_LLM))

g.add_node(n(read_files_suggested_by_LLM), read_files_suggested_by_LLM)
g.add_edge(n(read_files_suggested_by_LLM), END)

retrieve_graph = g.compile()


with open("./graph_diagrams/retrieve_graph.png", "wb") as f:
    f.write(retrieve_graph.get_graph().draw_mermaid_png())
