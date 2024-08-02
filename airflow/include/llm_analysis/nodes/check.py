from varname import nameof as n
from ..state_schema import State
from langchain_core.pydantic_v1 import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    FunctionMessage,
    SystemMessage,
    HumanMessage,
)
import json
from ..common import chat_model, output_parser

def do_we_need_more_retrieval(state: State) -> bool:
    class Enough(BaseModel):

        rationale: str = Field(
            description="Think out loud if the hypothesis needs more examination or if it's enough to add to the final report for this repository.",
        )
        is_enough: bool

    prompt = ChatPromptTemplate.from_template(
        """
        You are a seasoned software engineer tasked to understand the provided repository. Before this step, you've already proposed a hypothesis about this repo and chosen files to look into to confirm your hypothesis. Now all the files are opened and collected for you. Examine if your hypothesis is coherent with the actual content of the files.

        Hypothesis: {hypothesis}

        Files to refer:
        {retrieved_code_snippets}
        """
    )

    chain = prompt | chat_model.with_structured_output(Enough)

    response = chain.invoke(
        {
            "hypothesis": hypothesis_dict["hypothesis"],
            "retrieved_code_snippets": state["retrieved_code_snippets"],
        }
    )

    if response.is_enough:
        return n(do_we_have_enough_hypotheses)
    else:
        return 

def do_we_have_enough_hypotheses(state: State):
    hypotheses = state["final_hypotheses"]
    print(f"collected {len(hypotheses)} hypotheses so far")

    if len(hypotheses) >= 5:
        return "__end__"