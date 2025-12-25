from typing import Annotated

from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel
import logging

from seller_template.dependencies import DependencyContainer
from content_core_sdk.model_registry.model_factory import get_model
from content_core_sdk.model_registry.chat_models import SupportedModels
from content_core_sdk.model_registry.config import ModelConfig

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an intelligent archivist agent that helps users accomplish tasks by using available tools.

Your capabilities:
- You have access to various MCP (Model Context Protocol) tools that can help you complete tasks
- Read tool descriptions carefully and use them appropriately
- When a user provides a task description, break it down into steps and use the available tools to complete it
- Provide clear, helpful responses based on the tool results
- If a tool fails, explain what went wrong and suggest alternatives

Always be thorough, accurate, and helpful in your responses."""


class AgentState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages]


class ArchivistGraphBuilder:
    """Builds and compiles the LangGraph agent for task execution."""

    def __init__(self, dependencies: DependencyContainer):
        self.dependencies = dependencies
        self.agent = self._build_agent()

    def _build_agent(self):
        """Build the LangGraph agent.
        
        Requires:
            - GOOGLE_API_KEY environment variable (for GEMINI_2_0_FLASH) or
            - TOGETHER_API_KEY environment variable (for Together AI models)
            - At least one MCP tool configured via MCP_SERVERS__* environment variables
        
        Raises:
            RuntimeError: If LLM initialization fails or no tools are available.
        """
        try:
            llm = get_model(SupportedModels.GEMINI_2_0_FLASH, google_api_key=ModelConfig().google_api_keys[0])
        except Exception as e:
            error_msg = f"Failed to initialize LLM for agent: {e}. LLM is required for task execution."
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

        tools = self.dependencies.search_tools
        if not tools:
            error_msg = "No tools available for agent. Configure MCP_SERVERS__* environment variables."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        llm_with_tools = llm.bind_tools(tools)

        def chatbot(state: AgentState):
            return {"messages": [llm_with_tools.invoke(state["messages"])]}

        graph_builder = StateGraph(AgentState)
        graph_builder.add_node("chatbot", chatbot)
        
        tool_node = ToolNode(tools=tools)
        graph_builder.add_node("tools", tool_node)

        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_conditional_edges(
            "chatbot",
            lambda state: "tools" if state["messages"][-1].tool_calls else END,
        )
        graph_builder.add_edge("tools", "chatbot")
        
        return graph_builder.compile()
