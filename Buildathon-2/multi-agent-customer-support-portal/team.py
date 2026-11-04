import os
from dotenv import load_dotenv
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

from agents.query_agent import create_query_agent
from agents.knowledge_agent import create_knowledge_agent
from agents.resolution_agent import create_resolution_agent
from agents.log_agent import create_log_agent

load_dotenv(override=True)  # Load environment variables from .env file

def build_support_team():
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add it to your .env file or environment before running."
        )

    model_client = OpenAIChatCompletionClient(
        model=model_name,
        api_key=api_key
    )

    query_agent = create_query_agent(model_client)
    knowledge_agent = create_knowledge_agent(model_client)
    resolution_agent = create_resolution_agent(model_client)
    log_agent = create_log_agent(model_client)

    # 1 pass through the 4 agents + 2 tool calls = ~6-8 messages max.
    # TextMentionTermination halts execution the moment Log_Agent prints TERMINATE_TICKET_LOGGED.
    termination_condition = (
        TextMentionTermination("TERMINATE_TICKET_LOGGED") |
        MaxMessageTermination(max_messages=8)
    )

    team = RoundRobinGroupChat(
        participants=[query_agent, knowledge_agent, resolution_agent, log_agent],
        termination_condition=termination_condition
    )
    return team