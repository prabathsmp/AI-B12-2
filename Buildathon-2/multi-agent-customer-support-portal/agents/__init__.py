"""
Agents package for AI Customer Support Automation Desk.
Exports factory initializers for the four primary AutoGen support agents.
"""

from .query_agent import create_query_agent
from .knowledge_agent import create_knowledge_agent
from .resolution_agent import create_resolution_agent
from .log_agent import create_log_agent

__all__ = [
    "create_query_agent",
    "create_knowledge_agent",
    "create_resolution_agent",
    "create_log_agent",
]