import unittest


class ActionExecutionTests(unittest.TestCase):

    def test_executes_approved_action(self):
        from ai_engine.app.actions import (
            ActionExecutor,
            ActionRequest,
        )

        request = ActionRequest(
            action_name="delete_customer",
            approved=True,
            tool_name="customer_tool",
            parameters={
                "customer_id": "123",
            },
        )

        executor = ActionExecutor()

        result = executor.execute(request)

        self.assertTrue(result.success)

    def test_rejects_unapproved_action(self):
        from ai_engine.app.actions import (
            ActionExecutor,
            ActionNotApprovedError,
            ActionRequest,
        )

        request = ActionRequest(
            action_name="delete_customer",
            approved=False,
            tool_name="customer_tool",
            parameters={
                "customer_id": "123",
            },
        )

        executor = ActionExecutor()

        with self.assertRaises(
            ActionNotApprovedError,
        ):
            executor.execute(request)

    def test_result_preserves_action_data(self):
        from ai_engine.app.actions import (
            ActionExecutor,
            ActionRequest,
        )

        request = ActionRequest(
            action_name="update_customer",
            approved=True,
            tool_name="customer_tool",
            parameters={
                "customer_id": "123",
                "status": "active",
            },
        )

        executor = ActionExecutor()

        result = executor.execute(request)

        self.assertEqual(
            result.action_name,
            "update_customer",
        )

        self.assertEqual(
            result.tool_name,
            "customer_tool",
        )

        self.assertEqual(
            result.parameters,
            {
                "customer_id": "123",
                "status": "active",
            },
        )

    def test_result_marks_successful_execution(self):
        from ai_engine.app.actions import (
            ActionExecutor,
            ActionRequest,
        )

        request = ActionRequest(
            action_name="update_customer_note",
            approved=True,
            tool_name="customer_tool",
            parameters={},
        )

        executor = ActionExecutor()

        result = executor.execute(request)

        self.assertTrue(
            result.success,
        )


if __name__ == "__main__":
    unittest.main()
