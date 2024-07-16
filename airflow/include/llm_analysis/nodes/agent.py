from varname import nameof as n
from enum import Enum
import pendulum

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    FunctionMessage,
    SystemMessage,
    HumanMessage,
)
from ..state_schema import State

from ..common import llm, chat_model, output_parser
from ..tools import tools

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda


def agent(state: State):
    print("\n==>> agent")
    print("messages: ", state["messages"])

    system_message = SystemMessage(
        content="""You are a software engineer who is working at Github. Recently you have been leading a project that analyzes repositories to write a technical report using Large Language Models. However, often the repositories are large and complex, which doesn't fit into the context length of LLMs. You have to select the most important code snippets and information from the repository to create a prompt for the LLM that is not exceeding the context length. You can read files
        """
    )
    human_message = HumanMessage(
        content=f"""Here are the information about the project:
            Title: {state["title"]}
            Description: {state["repo_description"]}
            Root path of the project: {state["repo_root_path"]}
            Packages used: {", ".join(state["packages_used"])}
            Directory Tree: {state["directory_tree"]}"""
    )

    chain = (
        lambda messages: [system_message, human_message] + messages
    ) | chat_model.bind_tools(tools)

    response = chain.invoke(state["messages"])
    print(f"==>> response: {response}")

    return {"messages": [response]}
