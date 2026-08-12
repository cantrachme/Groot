import unittest
from uuid import uuid4

from ai_engine.app.core.context import AIRequestContext
from ai_engine.app.services.ai_service import AIService


class AIEngineTests(unittest.TestCase):
    def test_ai_request_context(self):
        user_id = uuid4()
        organization_id = uuid4()
        request_id = uuid4()

        context = AIRequestContext(
            user_id=user_id,
            organization_id=organization_id,
            request_id=request_id,
        )

        self.assertEqual(context.user_id, user_id)
        self.assertEqual(context.organization_id, organization_id)
        self.assertEqual(context.request_id, request_id)

    def test_ai_service(self):
        context = AIRequestContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
        )

        response = AIService().handle(context, "Hello GROOT")

        self.assertEqual(response, "AI Engine received the request.")
