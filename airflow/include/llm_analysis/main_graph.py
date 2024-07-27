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
    agent_hypothesis,
    agent_confirmation,
    update_hypothesis_with_confirmation,
)
from .nodes.read_files import read_files
from .nodes.have_enough_hypotheses import have_enough_hypotheses
from .nodes.file_path_validation import validate_file_paths, correct_file_paths
from .nodes.find_next_hypothesis import find_next_hypothesis

g = StateGraph(State)
g.add_node("entry", RunnablePassthrough())
g.set_entry_point("entry")

g.add_edge("entry", n(agent_hypothesis))

g.add_node(n(agent_hypothesis), agent_hypothesis)
g.add_edge(n(agent_hypothesis), n(validate_file_paths))

g.add_node(n(validate_file_paths), validate_file_paths)
g.add_conditional_edges(
    n(validate_file_paths),
    lambda state: (
        n(correct_file_paths)
        if len(state["invalid_paths"]) > 0 and state["validate_count"] < 3
        else n(retrieve_code_snippets)
    ),
    to_path_map([n(correct_file_paths), n(read_files)]),
)

g.add_node(n(correct_file_paths), correct_file_paths)
g.add_edge(n(correct_file_paths), n(validate_file_paths))

g.add_node(n(retrieve_code_snippets), retrieve_code_snippets)
g.add_edge(n(retrieve_code_snippets), n(read_files))

g.add_node(n(read_files), read_files)
g.add_edge(n(read_files), n(agent_confirmation))


g.add_node(n(agent_confirmation), agent_confirmation)
g.add_edge(n(agent_confirmation), n(update_hypothesis_with_confirmation))

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
g.add_edge(n(find_next_hypothesis), n(agent_hypothesis))

langgraph_app = g.compile()


with open("./main_graph.png", "wb") as f:
    f.write(langgraph_app.get_graph().draw_mermaid_png())
