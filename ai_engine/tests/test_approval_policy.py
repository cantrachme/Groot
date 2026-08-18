import unittest


class ActionRiskTests(unittest.TestCase):

    def test_defines_read_risk(self):
        from ai_engine.app.approvals import ActionRisk

        self.assertEqual(
            ActionRisk.READ.value,
            "read",
        )

    def test_defines_low_risk(self):
        from ai_engine.app.approvals import ActionRisk

        self.assertEqual(
            ActionRisk.LOW.value,
            "low",
        )

    def test_defines_high_impact_risk(self):
        from ai_engine.app.approvals import ActionRisk

        self.assertEqual(
            ActionRisk.HIGH_IMPACT.value,
            "high_impact",
        )


class ApprovalRequirementTests(unittest.TestCase):

    def test_stores_approval_required(self):
        from ai_engine.app.approvals import (
            ActionRisk,
            ApprovalRequirement,
        )

        requirement = ApprovalRequirement(
            action_name="delete_customer",
            risk=ActionRisk.HIGH_IMPACT,
            approval_required=True,
        )

        self.assertEqual(
            requirement.action_name,
            "delete_customer",
        )
        self.assertEqual(
            requirement.risk,
            ActionRisk.HIGH_IMPACT,
        )
        self.assertTrue(
            requirement.approval_required,
        )


class ApprovalPolicyTests(unittest.TestCase):

    def test_read_actions_are_automatic(self):
        from ai_engine.app.approvals import (
            ActionRisk,
            ApprovalPolicy,
        )

        policy = ApprovalPolicy()

        requirement = policy.evaluate(
            action_name="get_customer",
            risk=ActionRisk.READ,
        )

        self.assertFalse(
            requirement.approval_required,
        )

    def test_low_risk_action_is_policy_dependent(self):
        from ai_engine.app.approvals import (
            ActionRisk,
            ApprovalPolicy,
        )

        policy = ApprovalPolicy()

        requirement = policy.evaluate(
            action_name="update_customer_note",
            risk=ActionRisk.LOW,
        )

        self.assertFalse(
            requirement.approval_required,
        )

    def test_high_impact_action_requires_approval(self):
        from ai_engine.app.approvals import (
            ActionRisk,
            ApprovalPolicy,
        )

        policy = ApprovalPolicy()

        requirement = policy.evaluate(
            action_name="delete_customer",
            risk=ActionRisk.HIGH_IMPACT,
        )

        self.assertTrue(
            requirement.approval_required,
        )


if __name__ == "__main__":
    unittest.main()
