import logging
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from x402.clients.httpx import x402HttpxClient
from xy_market.clients.marketplace import MarketplaceClient

from buyer_example.config import get_settings
from buyer_example.tools import BuyerAgentTools

logger = logging.getLogger(__name__)


class BuyerAgentState(MessagesState):
    """State for Buyer Agent - extends MessagesState for LangGraph."""

    pass


class BuyerAgent:
    """LangGraph-based Buyer Agent."""

    def __init__(
        self,
        marketplace_client: MarketplaceClient,
        http_client: x402HttpxClient | None = None,
    ):
        """
        Initialize agent.

        Args:
            marketplace_client: MarketplaceClient for listing sellers
            http_client: Optional x402 HTTP client for seller interactions

        """
        self.settings = get_settings()
        self.marketplace_client = marketplace_client
        self.http_client = http_client

        # Initialize LLM - use first available API key
        if not self.settings.google_api_keys:
            raise RuntimeError(
                "No LLM API key configured. Set GOOGLE_API_KEYS in .env file. "
                "Example: GOOGLE_API_KEYS='[\"your-api-key\"]'"
            )

        self.llm = ChatGoogleGenerativeAI(
            google_api_key=self.settings.google_api_keys[0],
            model=self.settings.llm_model,
            temperature=0.7,
        )

        # Initialize tools
        tools = BuyerAgentTools(
            marketplace_client=marketplace_client,
            http_client=http_client,
        ).get_tools()
        self.llm_with_tools = self.llm.bind_tools(tools)

        # Build graph
        self.graph = self._build_graph(tools)

    def _build_graph(self, tools: list) -> StateGraph:
        """
        Build LangGraph state graph.

        Args:
            tools: List of LangChain tools

        Returns:
            Compiled graph

        """
        graph = StateGraph(BuyerAgentState)

        # Add nodes
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(tools))

        # Set entry point
        graph.set_entry_point("agent")

        # Add edges
        graph.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END,
            },
        )
        graph.add_edge("tools", "agent")

        return graph.compile()

    def _agent_node(self, state: BuyerAgentState) -> BuyerAgentState:
        """
        Agent node that calls LLM.

        Args:
            state: Current state

        Returns:
            Updated state with LLM response

        """
        messages = state.get("messages", [])

        # Add system prompt if this is the first message
        if not messages or not any(isinstance(m, SystemMessage) for m in messages):
            system_prompt = """You are a helpful Buyer Agent that helps users find and hire Seller Agents to complete tasks.

Your workflow:
1. When the user asks about a task, use the search_sellers tool to find relevant sellers
2. Present the sellers to the user in a clear, numbered format with their descriptions
3. If the user hasn't selected a seller yet, ask them which seller they'd like to use
4. IMPORTANT: Before executing a task, ALWAYS check the seller's pricing using check_seller_pricing tool (if available) and inform the user
5. Once the user confirms or selects a seller, use execute_task tool with that seller's information
6. After executing, use poll_task_status to wait for completion (keep polling until status is "done" or "failed")
7. Present the final result to the user in a clear, helpful format

Be conversational and helpful. Always explain what you're doing step by step."""
            messages = [SystemMessage(content=system_prompt)] + messages

        # Call LLM
        response = self.llm_with_tools.invoke(messages)

        # Update state
        return {"messages": [response]}

    def _should_continue(self, state: BuyerAgentState) -> Literal["continue", "end"]:
        """
        Determine if we should continue or end.

        Args:
            state: Current state

        Returns:
            "continue" if tools should be called, "end" otherwise

        """
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None

        if not last_message:
            return "end"

        # If LLM wants to call tools, continue
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"

        return "end"

    async def process_message(self, user_message: str) -> dict[str, Any]:
        """
        Process a user message.

        Args:
            user_message: User input

        Returns:
            Result dictionary with response and conversation history

        """
        initial_state: BuyerAgentState = {
            "messages": [HumanMessage(content=user_message)],
        }

        # Run graph
        final_state = await self.graph.ainvoke(initial_state)

        # Extract final response
        messages = final_state.get("messages", [])
        final_response = None

        # Find the last AI message (response to user)
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                final_response = msg.content
                break

        return {
            "status": "success",
            "response": final_response or "Task completed",
            "conversation": [
                {
                    "role": "user"
                    if isinstance(m, HumanMessage)
                    else "assistant"
                    if isinstance(m, AIMessage)
                    else "system",
                    "content": m.content if hasattr(m, "content") else str(m),
                }
                for m in messages
            ],
        }
