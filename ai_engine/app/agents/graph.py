from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .agent import Agent
from .context import AgentContext
from .result import AgentResult


class AgentGraphState(TypedDict):
    """State flowing through a GROOT agent graph."""

    context: AgentContext
    result: AgentResult | None


class AgentGraph:
    """LangGraph execution wrapper for a GROOT agent."""

    def __init__(
        self,
        agent: Agent,
    ) -> None:
        self.agent = agent
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentGraphState)

        workflow.add_node(
            "execute_agent",
            self._execute_agent,
        )

        workflow.add_edge(
            START,
            "execute_agent",
        )

        workflow.add_edge(
            "execute_agent",
            END,
        )

        return workflow.compile()

    def _execute_agent(
        self,
        state: AgentGraphState,
    ) -> dict:
        result = self.agent.execute(
            state["context"],
        )

        return {
            "result": result,
        }

    def invoke(
        self,
        context: AgentContext,
    ) -> AgentResult:
        result = self.graph.invoke(
            {
                "context": context,
                "result": None,
            }
        )

        return result["result"]
