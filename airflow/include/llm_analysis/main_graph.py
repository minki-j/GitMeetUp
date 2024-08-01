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
from .nodes.agent import (
    hypothesis,
    confirmation,
    update_hypothesis_with_confirmation,
)
from .nodes.read_files import read_files
from .nodes.have_enough_hypotheses import have_enough_hypotheses
from .nodes.file_path_validation import validate_file_paths, correct_file_paths
from .nodes.find_next_hypothesis import find_next_hypothesis
from .nodes.retrieve_code_snippets import retrieve_code_snippets

g = StateGraph(State)
g.add_node("entry", RunnablePassthrough())
g.set_entry_point("entry")

g.add_edge("entry", n(hypothesis))

g.add_node(n(hypothesis), hypothesis)
g.add_edge(n(hypothesis), n(retrieve_code_snippets))

g.add_node(n(retrieve_code_snippets), retrieve_code_snippets)
g.add_edge(n(retrieve_code_snippets), n(confirmation))

g.add_node(n(confirmation), confirmation)
g.add_edge(n(confirmation), n(update_hypothesis_with_confirmation))

g.add_node(n(update_hypothesis_with_confirmation), update_hypothesis_with_confirmation)
g.add_conditional_edges(
    n(update_hypothesis_with_confirmation),
    have_enough_hypotheses,
    to_path_map(
        [
            n(find_next_hypothesis),
            "__end__",
        ]
    ),
)

g.add_node(n(find_next_hypothesis), find_next_hypothesis)
g.add_edge(n(find_next_hypothesis), n(hypothesis))

langgraph_app = g.compile()


# with open("./main_graph.png", "wb") as f:
#     f.write(langgraph_app.get_graph().draw_mermaid_png())
