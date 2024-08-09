from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI, OpenAI
from langchain_core.runnables import ConfigurableField
# from airflow.models import Variable


output_parser = StrOutputParser()

# chat_model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7).configurable_fields(
#     temperature=ConfigurableField(
#         id="llm_temperature",
#         name="LLM Temperature",
#         description="The temperature of the LLM",
#     )
# )

# chat_model = ChatOpenAI(model="gpt-4o", temperature=0.7).configurable_fields(
#     temperature=ConfigurableField(
#         id="llm_temperature",
#         name="LLM Temperature",
#         description="The temperature of the LLM",
#     )
# )

# llm = OpenAI(model="gpt-3.5-turbo")

# llm = OpenAI(model="gpt-4o", temperature=0.7).configurable_fields(
#     temperature=ConfigurableField(
#         id="llm_temperature",
#         name="LLM Temperature",
#         description="The temperature of the LLM",
#     )
# )

from langchain_anthropic import ChatAnthropic, Anthropic

from dotenv import load_dotenv
import os

load_dotenv()

env = os.environ
chat_model = ChatAnthropic(
    model="claude-3-haiku-20240307", api_key=os.getenv("ANTHROPIC_API_KEY")
)
# chat_model = ChatAnthropic(
#     model="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY")
# )
# chat_model = ChatAnthropic(
#     model="claude-3-5-sonnet-20240620", api_key=Variable.get("ANTHROPIC_API_KEY")
# )

# llm = Anthropic(model="claude-3-haiku-20240307")

# llm = Anthropic(
#     model="claude-3-5-sonnet-20240620", api_key=Variable.get("ANTHROPIC_API_KEY")
# )
