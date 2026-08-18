import unittest


class ActionVerificationTests(unittest.TestCase):

    def test_verification_stores_action_result(self):
        from ai_engine.app.verification import VerificationResult

        result = VerificationResult(
            action_name="delete_customer",
            verified=True,
            details="Customer deletion confirmed.",
        )

        self.assertEqual(
            result.action_name,
            "delete_customer",
        )

        self.assertTrue(
            result.verified,
        )

        self.assertEqual(
            result.details,
            "Customer deletion confirmed.",
        )

    def test_verifies_successful_action(self):
        from ai_engine.app.actions import ActionResult
        from ai_engine.app.verification import ActionVerifier

        action_result = ActionResult(
            action_name="update_customer",
            tool_name="customer_tool",
            parameters={},
            success=True,
        )

        verifier = ActionVerifier()

        result = verifier.verify(action_result)

        self.assertTrue(
            result.verified,
        )

    def test_rejects_failed_action_verification(self):
        from ai_engine.app.actions import ActionResult
        from ai_engine.app.verification import ActionVerifier

        action_result = ActionResult(
            action_name="delete_customer",
            tool_name="customer_tool",
            parameters={},
            success=False,
        )

        verifier = ActionVerifier()

        result = verifier.verify(action_result)

        self.assertFalse(
            result.verified,
        )

    def test_preserves_action_name_during_verification(self):
        from ai_engine.app.actions import ActionResult
        from ai_engine.app.verification import ActionVerifier

        action_result = ActionResult(
            action_name="update_customer_note",
            tool_name="customer_tool",
            parameters={},
            success=True,
        )

        verifier = ActionVerifier()

        result = verifier.verify(action_result)

        self.assertEqual(
            result.action_name,
            "update_customer_note",
        )


if __name__ == "__main__":
    unittest.main()
