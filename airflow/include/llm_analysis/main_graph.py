from varname import nameof as n

from langgraph.graph import END, StateGraph
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from langgraph.prebuilt.tool_executor import ToolExecutor, ToolInvocation
from langgraph.prebuilt.tool_node import ToolNode
from langchain_core.messages import (
    HumanMessage,
)

from .utils.converters import to_path_map
from .state_schema import State
from .nodes.hypothesis import generate_hypothesis, evaluate_hypothesis
from .nodes.read_files import read_files_suggested_by_LLM
from .nodes.check import do_we_need_more_retrieval, do_we_have_enough_hypotheses
from .nodes.file_path_validation import validate_file_paths_from_LLM, correct_file_paths
from .nodes.find_next_hypothesis import find_next_hypothesis
from .nodes.retrieve_code_snippets import retrieve_code_by_hybrid_search_with_queries
from .nodes.clone_repo import clone_repo
from .subgraphs.retrieve.graph import retrieve_graph

g = StateGraph(State)
g.add_node("entry", RunnablePassthrough())
g.set_entry_point("entry")
g.add_edge("entry", n(clone_repo))

g.add_node(n(clone_repo), clone_repo)
g.add_edge(n(clone_repo), n(generate_hypothesis))

g.add_node(n(generate_hypothesis), generate_hypothesis)
g.add_edge(n(generate_hypothesis), n(retrieve_graph))

g.add_node(n(retrieve_graph), retrieve_graph)
g.add_edge(n(retrieve_graph), n(evaluate_hypothesis))

g.add_node(n(evaluate_hypothesis), evaluate_hypothesis)
g.add_conditional_edges(
    n(evaluate_hypothesis),
    do_we_need_more_retrieval,
    to_path_map(
        [
            n(do_we_have_enough_hypotheses),
            n(retrieve_graph),
        ]
    ),
)

g.add_node(n(do_we_have_enough_hypotheses), RunnablePassthrough())
g.add_conditional_edges(
    n(do_we_have_enough_hypotheses),
    do_we_have_enough_hypotheses,
    to_path_map(
        [
            n(generate_hypothesis),
            "__end__",
        ]
    ),
)

langgraph_app = g.compile()


with open("./graph_diagrams/main_graph.png", "wb") as f:
    f.write(langgraph_app.get_graph().draw_mermaid_png())
