from varname import nameof as n
from enum import Enum
import pendulum
import json

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    FunctionMessage,
    SystemMessage,
    HumanMessage,
)
from ..state_schema import State

from ..common import chat_model, output_parser
from ..tools import tools

from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List
from langchain_core.tools import tool
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda


class Hypothesis(BaseModel):
    """This is a Hypothesis of the repository. You must follow the order below when generating the properties
    1. rationale 2. hypothesis 3.queries_for_code_retrieval"""

    rationale: str = Field(description="The reason for the hypothesis and the queries to retreive codes for confirmation")
    hypothesis: str
    queries: List[str] = Field(
        description="A list of search queries used to retrieve relevant code snippets. These snippets will be used to verify the hypothesis. The retrieval process combines BM25 and embedding vector search techniques for improved accuracy. Order the queries from most imporant to least important."
    )


def hypothesis(state: State):
    print("==>> hypothesis node started")

    system_message = SystemMessage(
        content="""
        You are a sesoned software engineer tasked to understand the provided repository. It includes meta data such as title, description, directory tree, and packages used. 
        Based on the information, make a hypothesis about the project and queries that could be used to retrieve relevant code snippets to validate your hypothesis. The queries are english sentences that describe functionality or patterns in the code that you need to look at to confirm the hypothesis. For example, if your hypothsis includes "this repo contains third partry authentications, then queries could be "code for third party authentication", "login with google" etc.
        """
    )

    human_message = HumanMessage(
        content=f"""
        Here are the meta data of the repository:
        Title: {state["title"]}
        Description: {state["repo_description_by_user"]}
        Packages used: {", ".join(state["packages_used"])}
        Directory Tree: {state["directory_tree"]}
        """
    )

    chain = (
        lambda messages: [system_message, human_message] + messages
    ) | chat_model.with_structured_output(Hypothesis)

    response = chain.invoke(state["messages"])
    response_dict = response.dict()
    response_json = json.dumps(response_dict)

    return {"messages": [AIMessage(content=response_json)]}


def confirmation(state: State):
    print("==>> confirmation node started")

    hypothesis_json = state["messages"][-1]
    hypothesis_dict = json.loads(hypothesis_json.content)

    class Confirmation(BaseModel):
        """This is a result of the examination. You need to first provide the rationale of the result and then the boolean result for confirmation."""

        rationale: str = Field(
            description="Think out loud how you examined the hypothesis with the opened files. You must provide  rationale BEFORE confirmed to ensure a better and thoughful examiniation process.",
        )
        confirmed: bool = Field(
            description="True is the hypothesis is confirmed, False otherwise."
        )

    prompt = ChatPromptTemplate.from_template(
        """
        You are a seasoned software engineer tasked to understand the provided repository. Before this step, you've already proposed a hypothesis about this repo and chosen files to look into to confirm your hypothesis. Now all the files are opened and collected for you. Examine if your hypothesis is coherent with the actual content of the files.

        Hypothesis: {hypothesis}
        Rationale: {rationale}
        Files to refer:
        {retrieved_code_snippets}
        """
    )

    chain = prompt | chat_model.with_structured_output(Confirmation)

    response = chain.invoke(
        {
            "rationale": hypothesis_dict["rationale"],
            "hypothesis": hypothesis_dict["hypothesis"],
            "retrieved_code_snippets": state["retrieved_code_snippets"],
        }
    )

    result = response.dict()
    result["hypothesis"] = hypothesis_dict["hypothesis"]

    return {"analysis_results": [result]}


def update_hypothesis_with_confirmation(state: State):
    print("==>> update_hypothesis_with_confirmation node started")

    hypothesis_json = state["messages"][-1]
    hypothesis_dict = json.loads(hypothesis_json.content)
    confirmation = state["analysis_results"][-1]

    class UpdatedHypothesis(BaseModel):
        hypothesis: str = Field(
            description="This is a new hypothesis that has been updated based on the confirmation results",
        )

    prompt = ChatPromptTemplate.from_template(
        """
You are a sesoned software engineering tasked to understand the provided repository. Before this step, you've proposed a hypothesis about this repo and examined the hypothesis by actually looking into codebase. There are extra information that has been revealed during the examination. Based on the new insights, please provide an updated hypothesis for the project:

Original hypothesis: {original_hypothesis}
Examination result: {confirmation_rationale}
        """
    )

    chain = prompt | chat_model.with_structured_output(UpdatedHypothesis)

    updated_hypothesis = chain.invoke(
        {
            "original_hypothesis": hypothesis_dict["hypothesis"],
            "confirmation_rationale": confirmation["rationale"],
        }
    ).hypothesis

    return {"final_hypotheses": [updated_hypothesis]}
