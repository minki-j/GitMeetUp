from ..state_schema import State
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    FunctionMessage,
    SystemMessage,
    HumanMessage,
)


def find_next_hypothesis(state: State):
    return {
        "messages": HumanMessage(
            content=f"""
    Your hypothesis is {"successfully confirmed" if state["analysis_results"][-1]["confirmed"] else "rejected"} for the following reason:
    {state["analysis_results"][-1]["rationale"]}
    ---
    Now, let's move on to the next hypothesis. Suggest a new hypothesis and the file paths you want to examine to confirm."""
        )
    }
