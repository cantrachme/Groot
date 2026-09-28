import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

from pydantic import ConfigDict, Field

from ai_engine.app.actions import ActionRequest, ActionResult
from ai_engine.app.actions.pipeline import ControlledActionPipeline
from ai_engine.app.actions.registry import (
    ActionDefinition,
    ActionParameters,
    ActionRegistry,
)
from ai_engine.app.agents import (
    Agent,
    AgentContext,
    AgentRegistry,
    AgentResult,
    AgentSelection,
    AgentSupervisor,
    MultiAgentCoordinator,
)
from ai_engine.app.approvals import ActionRisk, ApprovalPolicy
from ai_engine.app.audit import AuditEvent, AuditLog
from ai_engine.app.permissions import AuthorizationContext, Permission, Role
from ai_engine.app.verification import VerificationResult


class Parameters(ActionParameters):
    target: int = Field(gt=0)
    note: str = ""


class TestAgent(Agent):
    name = "operator_agent"
    description = "Test action proposer"
    capabilities = ("propose",)
    allowed_tools = ("local_tool",)

    def execute(self, context):
        return AgentResult(
            True,
            self.name,
            "Proposed action",
            tool_calls=({"name": "local_tool", "arguments": {"target": 1}},),
        )


class ControlledActionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "audit.jsonl"
        self.log = AuditLog(self.path)
        self.registry = ActionRegistry()
        self.calls = []
        self.checks = []

        def execute(request, context):
            self.calls.append((request, context))
            return True

        def verify(result, context, parameters):
            self.checks.append((result, context, parameters))
            return parameters["target"] == 1

        self.definition = ActionDefinition(
            "local_action",
            "local_tool",
            Permission("local", "execute"),
            ActionRisk.HIGH_IMPACT,
            Parameters,
            execute,
            verify,
        )
        self.registry.register(self.definition)
        self.pipeline = ControlledActionPipeline(self.registry, self.log)
        self.agent = TestAgent()
        self.context = AgentContext(
            7,
            11,
            uuid4(),
            "private-task-secret",
            {"secret": "context-secret"},
            frozenset({"local.execute"}),
        )
        self.authority = AuthorizationContext(
            7,
            11,
            (Role("operator", (Permission("local", "execute"),)),),
            self.agent.name,
        )
        self.human = AuthorizationContext(
            9, 11, (Role("approver", (Permission("actions", "approve"),)),), "human"
        )
        self.request = ActionRequest(
            "local_action", False, "local_tool", {"target": 1, "note": "payload-secret"}
        )

    def configure(self, **changes):
        self.registry = ActionRegistry()
        self.registry.register(replace(self.definition, **changes))
        self.pipeline = ControlledActionPipeline(self.registry, self.log)

    def submit(self, request=None, **changes):
        args = {
            "agent": self.agent,
            "context": self.context,
            "authorization": self.authority,
            **changes,
        }
        return self.pipeline.submit(
            request if request is not None else self.request, **args
        )

    def execute(self, operation_id, **changes):
        return self.pipeline.execute(
            operation_id,
            **{
                "agent": self.agent,
                "context": self.context,
                "authorization": self.authority,
                **changes,
            },
        )

    def approved(self):
        executions_before = len(self.calls)
        pending = self.submit()
        approved = self.pipeline.decide(
            pending.operation_id, approver=self.human, approved=True
        )
        self.assertEqual(approved.status, "approved")
        self.assertFalse(approved.success)
        self.assertEqual(len(self.calls), executions_before)
        return pending.operation_id

    def test_read_and_low_risk_execute_automatically_by_existing_policy(self):
        for risk in (ActionRisk.READ, ActionRisk.LOW):
            with self.subTest(risk=risk):
                self.configure(risk=risk)
                result = self.submit()
                self.assertTrue(result.success)
                self.assertFalse(result.requirement.approval_required)
                self.assertIsInstance(result.execution, ActionResult)
                self.assertTrue(result.verification.verified)
                self.assertEqual(result.execution.parameters, {})
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(self.checks), 2)

    def test_high_impact_waits_for_separate_human_approval(self):
        result = self.submit()
        self.assertEqual(result.status, "approval_required")
        self.assertTrue(result.requirement.approval_required)
        self.assertIsNone(result.execution)
        self.assertEqual(self.calls, [])
        blocked = self.execute(result.operation_id)
        self.assertEqual(blocked.status, "approval_required")
        self.assertIn(
            "action.execution_blocked", [event.event_name for event in self.log.events]
        )
        self.assertEqual(self.calls, [])

    def test_incoming_approved_boolean_never_bypasses_human_approval(self):
        result = self.submit(replace(self.request, approved=True))
        self.assertEqual(result.status, "approval_required")
        self.assertEqual(self.execute(result.operation_id).status, "approval_required")
        self.assertEqual(self.calls, [])

    def test_approved_action_executes_once_through_executor_and_verifier(self):
        operation_id = self.approved()
        self.pipeline.executor.execute = Mock(wraps=self.pipeline.executor.execute)
        self.pipeline.verifier.verify = Mock(wraps=self.pipeline.verifier.verify)
        first = self.execute(operation_id)
        second = self.execute(operation_id)
        self.assertEqual(first, second)
        self.assertTrue(first.success)
        self.assertEqual(self.pipeline.executor.execute.call_count, 1)
        self.assertEqual(self.pipeline.verifier.verify.call_count, 1)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(self.checks), 1)
        self.assertIsInstance(first.execution, ActionResult)
        self.assertTrue(first.verification.verified)

    def test_unauthorized_roles_context_grant_and_agent_allowlist_never_execute(self):
        for authority, context, allowed in (
            (replace(self.authority, roles=()), self.context, ("local_tool",)),
            (
                self.authority,
                replace(self.context, permissions=frozenset()),
                ("local_tool",),
            ),
            (self.authority, self.context, ()),
        ):
            with self.subTest(authority=authority, allowed=allowed):
                self.agent.allowed_tools = allowed
                result = self.submit(authorization=authority, context=context)
                self.assertEqual(result.status, "unauthorized")
        self.assertEqual(self.calls, [])
        self.assertEqual(self.checks, [])

    def test_registered_verifier_checks_observed_local_effect(self):
        observed = {}

        def execute(request, context):
            observed[(context.organization_id, request.parameters["target"])] = True
            return True

        def verify(result, context, parameters):
            return observed.get((context.organization_id, parameters["target"])) is True

        self.configure(execute=execute, verify=verify)
        result = self.execute(self.approved())
        self.assertTrue(result.success)
        self.assertEqual(observed, {(11, 1): True})

        observed.clear()
        self.configure(execute=lambda request, context: True, verify=verify)
        result = self.execute(self.approved())
        self.assertTrue(result.execution.success)
        self.assertFalse(result.verification.verified)
        self.assertEqual(result.status, "verification_failed")

    def test_knowledge_read_permission_does_not_grant_action_authority(self):
        auth = replace(
            self.authority, roles=(Role("member", (Permission("knowledge", "read"),)),)
        )
        result = self.submit(authorization=auth)
        self.assertEqual(result.status, "unauthorized")
        self.assertEqual(self.calls, [])

    def test_mismatched_user_tenant_and_agent_authority_are_rejected(self):
        for changes in (
            {"user_id": 99},
            {"organization_id": 99},
            {"agent_name": "another"},
            {"user_id": True},
        ):
            with self.subTest(changes=changes):
                self.assertEqual(
                    self.submit(
                        authorization=replace(self.authority, **changes)
                    ).status,
                    "unauthorized",
                )
        self.assertEqual(self.calls, [])

    def test_human_approval_requires_permission_matching_tenant_and_human_entry(self):
        pending = self.submit()
        for approver in (
            replace(self.human, roles=()),
            replace(self.human, organization_id=99),
            replace(self.human, agent_name=self.agent.name),
            replace(self.human, user_id=True),
        ):
            with self.subTest(approver=approver), self.assertRaises(PermissionError):
                self.pipeline.decide(
                    pending.operation_id, approver=approver, approved=True
                )
        self.assertEqual(self.execute(pending.operation_id).status, "approval_required")
        self.assertEqual(self.calls, [])

    def test_denied_action_cannot_be_approved_or_executed_later(self):
        pending = self.submit()
        result = self.pipeline.decide(
            pending.operation_id, approver=self.human, approved=False
        )
        self.assertEqual(result.status, "denied")
        self.assertEqual(self.execute(pending.operation_id).status, "denied")
        with self.assertRaises(ValueError):
            self.pipeline.decide(
                pending.operation_id, approver=self.human, approved=True
            )
        self.assertEqual(self.calls, [])

    def test_permission_revocation_after_approval_blocks_execution(self):
        operation_id = self.approved()
        result = self.execute(
            operation_id, authorization=replace(self.authority, roles=())
        )
        self.assertEqual(result.status, "unauthorized")
        self.assertEqual(self.calls, [])

    def test_approval_is_bound_to_captured_parameters(self):
        pending = self.submit()
        self.request.parameters["target"] = 999
        self.request.parameters["note"] = "mutated-secret"
        self.pipeline.decide(pending.operation_id, approver=self.human, approved=True)
        result = self.execute(pending.operation_id)
        self.assertTrue(result.success)
        self.assertEqual(self.calls[0][0].parameters["target"], 1)
        self.assertEqual(self.calls[0][0].parameters["note"], "payload-secret")

    def test_execution_cannot_mutate_verification_target(self):
        def execute(request, context):
            request.parameters["target"] = 999
            return True

        self.configure(execute=execute)
        result = self.execute(self.approved())
        self.assertTrue(result.success)
        self.assertEqual(self.checks[0][2]["target"], 1)

    def test_context_survives_execution_verification_and_audit(self):
        result = self.execute(self.approved())
        self.assertIs(self.calls[0][1], self.context)
        self.assertIs(self.checks[0][1], self.context)
        self.assertEqual(
            (
                result.context.user_id,
                result.context.organization_id,
                result.context.request_id,
                result.agent_name,
            ),
            (7, 11, self.context.request_id, self.agent.name),
        )
        for event in self.log.events:
            self.assertEqual(
                (
                    event.user_id,
                    event.organization_id,
                    event.agent_name,
                    event.request_id,
                ),
                (7, 11, self.agent.name, self.context.request_id),
            )
        approval = next(
            event for event in self.log.events if event.event_name == "action.approved"
        )
        self.assertEqual(approval.actor_user_id, 9)

    def test_different_context_cannot_resume_operation(self):
        operation_id = self.approved()
        for changes in (
            {"user_id": 8},
            {"organization_id": 12},
            {"request_id": uuid4()},
        ):
            with self.subTest(changes=changes), self.assertRaises(PermissionError):
                self.execute(operation_id, context=replace(self.context, **changes))
        self.assertEqual(self.calls, [])

    def test_failed_verification_stays_failed_on_replay(self):
        self.configure(verify=lambda result, context, parameters: False)
        result = self.execute(self.approved())
        self.assertEqual(result.status, "verification_failed")
        self.assertFalse(result.success)
        self.assertTrue(result.execution.success)
        self.assertFalse(result.verification.verified)
        self.assertEqual(self.execute(result.operation_id), result)
        self.assertEqual(len(self.calls), 1)

    def test_handler_exception_is_failed_and_still_passes_through_verifier(self):
        def execute(request, context):
            raise RuntimeError("provider-token-secret")

        self.configure(execute=execute)
        self.pipeline.verifier.verify = Mock(wraps=self.pipeline.verifier.verify)
        result = self.execute(self.approved())
        self.assertEqual(result.status, "execution_failed")
        self.assertIsInstance(result.execution, ActionResult)
        self.assertFalse(result.execution.success)
        self.assertFalse(result.verification.verified)
        self.assertEqual(self.pipeline.verifier.verify.call_count, 1)
        self.assertNotIn("provider-token-secret", repr(result) + self.path.read_text())

    def test_false_or_nonboolean_callback_results_fail_closed(self):
        for callback_value in (False, "yes-secret", {"token": "output-secret"}, None):
            with self.subTest(value=callback_value):
                self.configure(
                    risk=ActionRisk.READ,
                    execute=lambda request, context, value=callback_value: value,
                )
                result = self.submit()
                self.assertFalse(result.success)
                self.assertEqual(result.status, "execution_failed")
                self.assertFalse(result.verification.verified)

    def test_verifier_exception_and_raw_details_do_not_escape(self):
        def verify(result, context, parameters):
            raise RuntimeError("verification-secret")

        self.configure(verify=verify)
        result = self.execute(self.approved())
        self.assertEqual(result.status, "verification_failed")
        self.assertNotIn("verification-secret", repr(result) + self.path.read_text())
        self.configure(risk=ActionRisk.READ)
        self.pipeline.verifier.verify = Mock(
            return_value=VerificationResult("local_action", False, "raw-secret")
        )
        result = self.submit()
        self.assertEqual(result.status, "verification_failed")
        self.assertNotIn("raw-secret", repr(result))

    def test_failed_execution_cannot_be_upgraded_by_verifier(self):
        self.configure(risk=ActionRisk.READ, execute=lambda request, context: False)
        self.pipeline.verifier.verify = Mock(
            return_value=VerificationResult("local_action", True, "incorrect")
        )
        result = self.submit()
        self.assertEqual(result.status, "execution_failed")
        self.assertFalse(result.verification.verified)

    def test_invalid_requests_are_rejected_without_echoing_input(self):
        for request in (
            "invalid-secret",
            replace(self.request, action_name="unknown-secret"),
            replace(self.request, tool_name="tool-secret"),
            replace(self.request, approved="yes-secret"),
            replace(self.request, parameters={"target": "1"}),
            replace(
                self.request, parameters={"target": 1, "risk": "read", "approved": True}
            ),
            replace(self.request, parameters={"target": 0}),
        ):
            with self.subTest(request=request):
                result = self.submit(request)
                self.assertEqual(result.status, "invalid")
                self.assertIsNone(result.execution)
        self.assertEqual(self.calls, [])
        for value in ("invalid-secret", "unknown-secret", "tool-secret", "yes-secret"):
            self.assertNotIn(value, self.path.read_text())

    def test_secrets_are_omitted_from_all_results_and_journal(self):
        pending = self.submit()
        approved = self.pipeline.decide(
            pending.operation_id, approver=self.human, approved=True
        )
        result = self.execute(pending.operation_id)
        serialized = (
            repr((pending, approved, result, self.log.events)) + self.path.read_text()
        )
        for secret in ("payload-secret", "private-task-secret", "context-secret"):
            self.assertNotIn(secret, serialized)
        self.assertEqual(result.execution.parameters, {})

    def test_audit_events_cover_decisions_execution_and_verification_in_order(self):
        result = self.execute(self.approved())
        self.assertEqual(
            [event.event_name for event in self.log.events],
            [
                "action.requested",
                "action.authorized",
                "action.risk_classified",
                "action.approval_required",
                "action.approved",
                "action.execution_started",
                "action.executed",
                "action.verified",
            ],
        )
        self.assertTrue(
            all(event.operation_id == result.operation_id for event in self.log.events)
        )
        self.assertEqual(AuditLog(self.path).events, self.log.events)
        self.assertEqual(len(self.path.read_text().splitlines()), 8)
        self.assertTrue(
            all(
                json.loads(line)["request_id"] == str(self.context.request_id)
                for line in self.path.read_text().splitlines()
            )
        )

    def test_audit_failure_before_execution_blocks_handler(self):
        self.configure(risk=ActionRisk.READ)
        record = self.log.record

        def fail_started(event):
            if event.event_name == "action.execution_started":
                raise OSError("disk-secret")
            record(event)

        self.log.record = fail_started
        result = self.submit()
        self.assertEqual(result.status, "audit_failed")
        self.assertEqual(self.calls, [])
        self.assertNotIn("disk-secret", repr(result))

    def test_audit_failure_after_execution_still_verifies_and_never_reexecutes(self):
        self.configure(risk=ActionRisk.READ)
        record = self.log.record

        def fail_completed(event):
            if event.event_name == "action.executed":
                raise OSError("disk-secret")
            record(event)

        self.log.record = fail_completed
        result = self.submit()
        self.assertEqual(result.status, "audit_failed")
        self.assertEqual(len(self.checks), 1)
        self.assertEqual(self.execute(result.operation_id).status, "audit_failed")
        self.assertEqual(len(self.calls), 1)

    def test_approval_audit_failure_cannot_release_execution(self):
        pending = self.submit()
        self.log.record = Mock(side_effect=OSError("secret"))
        result = self.pipeline.decide(
            pending.operation_id, approver=self.human, approved=True
        )
        self.assertEqual(result.status, "audit_failed")
        self.assertEqual(self.execute(pending.operation_id).status, "audit_failed")
        self.assertEqual(self.calls, [])

    def test_restart_preserves_decisions_but_cannot_resume_payloads(self):
        operation_id = self.approved()
        restarted = ControlledActionPipeline(self.registry, AuditLog(self.path))
        with self.assertRaises(PermissionError):
            restarted.execute(
                operation_id,
                agent=self.agent,
                context=self.context,
                authorization=self.authority,
            )
        self.assertEqual(self.calls, [])
        self.assertTrue(
            any(
                event.event_name == "action.approved"
                for event in restarted.audit_log.events
            )
        )

    def test_concurrent_and_reentrant_attempts_do_not_execute_twice(self):
        operation_id = self.approved()
        with ThreadPoolExecutor(max_workers=4) as workers:
            results = list(workers.map(lambda _: self.execute(operation_id), range(4)))
        self.assertTrue(all(result.success for result in results))
        self.assertEqual(len(self.calls), 1)
        self.configure()
        operation_id = self.approved()
        original = self.pipeline.executor.execute

        def reentrant(request, **kwargs):
            self.assertEqual(self.execute(operation_id).status, "indeterminate")
            return original(request, **kwargs)

        self.pipeline.executor.execute = reentrant
        self.assertTrue(self.execute(operation_id).success)
        self.assertEqual(len(self.calls), 2)

    def test_coordinator_requires_explicit_handoff_and_reuses_registered_agent(self):
        registry = AgentRegistry()
        registry.register(self.agent)
        coordinator = MultiAgentCoordinator(AgentSupervisor(registry))
        coordinator.execute(
            AgentSelection((self.agent.name,), "Explicit"), self.context
        )
        self.assertEqual(self.calls, [])
        pending = coordinator.submit_action(
            self.request,
            agent_name=self.agent.name,
            context=self.context,
            authorization=self.authority,
            pipeline=self.pipeline,
        )
        self.assertEqual(pending.status, "approval_required")
        self.pipeline.decide(pending.operation_id, approver=self.human, approved=True)
        self.assertTrue(self.execute(pending.operation_id).success)

    def test_unknown_risk_and_unguarded_parameter_definitions_are_rejected(self):
        with self.assertRaises(TypeError):
            ApprovalPolicy().evaluate("local_action", "high_impact")
        with self.assertRaises(TypeError):
            ActionRegistry().register(replace(self.definition, risk="read"))

        class Loose(ActionParameters):
            model_config = ConfigDict(extra="allow")

        with self.assertRaises(ValueError):
            ActionRegistry().register(replace(self.definition, parameters_model=Loose))
        with self.assertRaises(ValueError):
            self.registry.register(self.definition)

    def test_in_memory_audit_is_not_enough_for_controlled_execution(self):
        with self.assertRaises(ValueError):
            ControlledActionPipeline(self.registry, AuditLog())

    def test_corrupt_journal_fails_closed(self):
        self.path.write_text('{"invalid":')
        with self.assertRaises(ValueError):
            AuditLog(self.path)

    def test_uuid_identity_round_trips_in_audit(self):
        event = AuditEvent(
            "test",
            uuid4(),
            uuid4(),
            "operator_agent",
            request_id=uuid4(),
            operation_id=uuid4(),
            actor_user_id=uuid4(),
        )
        self.log.record(event)
        self.assertEqual(AuditLog(self.path).events, (event,))

    def test_invalid_context_and_operation_id_are_never_written(self):
        with self.assertRaises(ValueError):
            self.submit(context=replace(self.context, user_id="identity-secret"))
        with self.assertRaises(ValueError):
            self.execute("operation-secret")
        self.assertEqual(self.log.events, ())
