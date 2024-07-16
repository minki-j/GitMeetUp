from varname import nameof as n

from langgraph.graph import END, StateGraph
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from langgraph.prebuilt.tool_executor import ToolExecutor, ToolInvocation
from langgraph.prebuilt.tool_node import ToolNode


from .utils.converters import to_path_map
from .state_schema import State
from .nodes.agent import agent
from .tools import tools

def should_continue(state: State):
    messages = state["messages"]
    print(f"==>> messages: {messages}")
    last_message = messages[-1]
    print("last_message.tool_calls: ", last_message.tool_calls)

    if not last_message.tool_calls:    
        return "end"
    else:
        return "continue"


g = StateGraph(State)
g.add_node("entry", RunnablePassthrough())
g.set_entry_point("entry")

g.add_edge("entry", n(agent))

g.add_node(n(agent), agent)
g.add_conditional_edges(
    n(agent),
    should_continue,
    {"continue": n(tools), "end": END},
)

g.add_node(n(tools), ToolNode(tools))
g.add_edge(n(tools), n(agent))


langgraph_app = g.compile()


with open("include/llm_analysis/graph_imgs/main_graph.png", "wb") as f:
    f.write(langgraph_app.get_graph().draw_mermaid_png())
