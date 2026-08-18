import unittest
from uuid import uuid4

from ai_engine.app.agents import (
    Agent,
    AgentContext,
    AgentResult,
    ResearchAgent,
)


class ResearchAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = ResearchAgent()

        self.context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="Compare two market reports.",
        )

    def test_implements_agent_contract(self):
        self.assertIsInstance(
            self.agent,
            Agent,
        )

    def test_defines_research_capabilities(self):
        self.assertEqual(
            self.agent.capabilities,
            (
                "research",
                "gather_evidence",
                "compare_information",
                "summarize",
                "cite_sources",
            ),
        )

    def test_returns_standardized_result(self):
        result = self.agent.execute(
            self.context,
        )

        self.assertIsInstance(
            result,
            AgentResult,
        )
        self.assertTrue(result.success)
        self.assertEqual(
            result.agent_name,
            "research_agent",
        )
        self.assertEqual(
            result.summary,
            "Research completed: Compare two market reports.",
        )

    def test_preserves_research_evidence(self):
        context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="Compare competitors.",
            state={
                "evidence": (
                    {
                        "source": "Report A",
                        "finding": "Revenue increased.",
                    },
                    {
                        "source": "Report B",
                        "finding": "Revenue remained stable.",
                    },
                ),
                "citations": (
                    "Report A",
                    "Report B",
                ),
            },
        )

        result = self.agent.execute(context)

        self.assertEqual(
            result.evidence,
            (
                {
                    "source": "Report A",
                    "finding": "Revenue increased.",
                },
                {
                    "source": "Report B",
                    "finding": "Revenue remained stable.",
                },
            ),
        )

        self.assertEqual(
            result.data["citations"],
            (
                "Report A",
                "Report B",
            ),
        )

    def test_preserves_comparison_and_summary(self):
        context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="Compare market performance.",
            state={
                "comparison": {
                    "winner": "Company A",
                },
                "summary": "Company A outperformed Company B.",
            },
        )

        result = self.agent.execute(context)

        self.assertEqual(
            result.data["comparison"],
            {
                "winner": "Company A",
            },
        )

        self.assertEqual(
            result.summary,
            "Company A outperformed Company B.",
        )


if __name__ == "__main__":
    unittest.main()
