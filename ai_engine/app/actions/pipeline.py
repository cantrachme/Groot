"""Explicit controlled actions; host authentication supplies all authority contexts."""

import json
import re
from dataclasses import dataclass, field
from threading import RLock
from uuid import UUID, uuid4

from ..agents.agent import Agent
from ..agents.capabilities import ToolPermission
from ..agents.context import AgentContext
from ..agents.policy import AgentCapabilityPolicy
from ..approvals.models import ApprovalRequirement
from ..approvals.policy import ApprovalPolicy
from ..audit import AuditEvent, AuditLog
from ..core.context import AIRequestContext
from ..permissions import AuthorizationContext, Permission, PermissionEngine
from ..verification import ActionVerifier, VerificationResult
from .executor import ActionExecutor
from .models import ActionRequest, ActionResult
from .registry import ActionDefinition, ActionRegistry


@dataclass(frozen=True)
class ControlledActionResult:
    operation_id: UUID
    context: AIRequestContext
    agent_name: str
    status: str
    requirement: ApprovalRequirement | None = None
    execution: ActionResult | None = None
    verification: VerificationResult | None = None

    @property
    def success(self) -> bool:
        return self.status == "succeeded"


@dataclass
class _Pending:
    operation_id: UUID
    context: AgentContext = field(repr=False)
    agent_name: str
    definition: ActionDefinition
    parameters_json: str = field(repr=False)
    requirement: ApprovalRequirement
    approval: str = "pending"
    terminal: ControlledActionResult | None = None


class ControlledActionPipeline:
    """Reuse permission, approval, executor, verifier and audit implementations.

    Approval decisions are a separate trusted human-host operation. No request
    flag, agent output, gesture or knowledge token is treated as human approval.
    The journal is durable; payloads and executable approvals are process-local.
    A restarted process rejects old operation IDs and requires a fresh request.
    """

    def __init__(self, registry: ActionRegistry, audit_log: AuditLog) -> None:
        if not audit_log.durable:
            raise ValueError("Controlled actions require a durable audit journal.")
        self.registry = registry
        self.audit_log = audit_log
        self.permissions = PermissionEngine()
        self.policy = ApprovalPolicy()
        self.executor = ActionExecutor(registry)
        self.verifier = ActionVerifier(registry)
        self._pending: dict[UUID, _Pending] = {}
        self._lock = RLock()

    @staticmethod
    def _identity(context: AgentContext, agent_name: str) -> AIRequestContext:
        if (
            not all(
                type(value) is UUID or type(value) is int and value > 0
                for value in (context.user_id, context.organization_id)
            )
            or type(context.request_id) is not UUID
        ):
            raise ValueError("Invalid action context.")
        if not isinstance(agent_name, str) or not re.fullmatch(
            r"[a-z][a-z0-9_.-]{0,79}", agent_name
        ):
            raise ValueError("Invalid action agent.")
        return AIRequestContext(
            context.user_id, context.organization_id, context.request_id
        )

    @staticmethod
    def _same(left: object, right: object) -> bool:
        return type(left) is type(right) and left == right

    def _authorize(
        self,
        definition: ActionDefinition,
        agent: Agent,
        context: AgentContext,
        authorization: AuthorizationContext,
    ) -> None:
        if not (
            self._same(context.user_id, authorization.user_id)
            and self._same(context.organization_id, authorization.organization_id)
            and agent.name == authorization.agent_name
        ):
            raise PermissionError("Action authority does not match its context.")
        self.permissions.authorize(authorization, definition.permission)
        AgentCapabilityPolicy(
            (ToolPermission(definition.tool_name, definition.permission.name),)
        ).authorize(
            agent,
            definition.tool_name,
            context,
        )

    def _event(
        self,
        name: str,
        operation_id: UUID,
        context: AgentContext,
        agent_name: str,
        definition: ActionDefinition | None = None,
        actor_user_id: int | UUID | None = None,
        error_type: str | None = None,
    ) -> bool:
        try:
            self.audit_log.record(
                AuditEvent(
                    event_name=name,
                    operation_id=operation_id,
                    request_id=context.request_id,
                    user_id=context.user_id,
                    organization_id=context.organization_id,
                    agent_name=agent_name,
                    actor_user_id=actor_user_id,
                    error_type=error_type,
                    action_name=definition.name if definition else None,
                    tool_name=definition.tool_name if definition else None,
                    risk=definition.risk.value if definition else None,
                )
            )
        except (OSError, ValueError, TypeError):
            return False
        return True

    def _outcome(
        self,
        item: _Pending,
        status: str,
        execution: ActionResult | None = None,
        verification: VerificationResult | None = None,
    ) -> ControlledActionResult:
        return ControlledActionResult(
            item.operation_id,
            self._identity(item.context, item.agent_name),
            item.agent_name,
            status,
            item.requirement,
            execution,
            verification,
        )

    def submit(
        self,
        request: ActionRequest,
        *,
        agent: Agent,
        context: AgentContext,
        authorization: AuthorizationContext,
    ) -> ControlledActionResult:
        identity = self._identity(context, agent.name)
        operation_id = uuid4()
        with self._lock:
            if not self._event("action.requested", operation_id, context, agent.name):
                return ControlledActionResult(
                    operation_id, identity, agent.name, "audit_failed"
                )
            try:
                if (
                    not isinstance(request, ActionRequest)
                    or type(request.approved) is not bool
                ):
                    raise ValueError("Invalid action request.")
                definition = self.registry.get(request.action_name)
                if request.tool_name != definition.tool_name:
                    raise ValueError("Action/tool mismatch.")
                parameters = definition.parameters_model.model_validate(
                    request.parameters
                )
                # Copy and serialize before approval; later mutations cannot change the target.
                encoded = json.dumps(
                    parameters.model_dump(mode="json"), allow_nan=False
                )
            except (ValueError, TypeError, KeyError, OverflowError):
                logged = self._event(
                    "action.invalid", operation_id, context, agent.name
                )
                return ControlledActionResult(
                    operation_id,
                    identity,
                    agent.name,
                    "invalid" if logged else "audit_failed",
                )
            try:
                self._authorize(definition, agent, context, authorization)
            except (PermissionError, TypeError, AttributeError):
                logged = self._event(
                    "action.unauthorized", operation_id, context, agent.name, definition
                )
                return ControlledActionResult(
                    operation_id,
                    identity,
                    agent.name,
                    "unauthorized" if logged else "audit_failed",
                )
            requirement = self.policy.evaluate(definition.name, definition.risk)
            item = _Pending(
                operation_id, context, agent.name, definition, encoded, requirement
            )
            self._pending[operation_id] = item
            for name in (
                "action.authorized",
                "action.risk_classified",
                "action.approval_required"
                if requirement.approval_required
                else "action.automatic",
            ):
                if not self._event(name, operation_id, context, agent.name, definition):
                    item.terminal = self._outcome(item, "audit_failed")
                    return item.terminal
            if requirement.approval_required:
                return self._outcome(item, "approval_required")
            item.approval = "automatic"
            return self._run(item)

    def decide(
        self, operation_id: UUID, *, approver: AuthorizationContext, approved: bool
    ) -> ControlledActionResult:
        """Called only by the host's authenticated human approval interface."""
        if type(operation_id) is not UUID:
            raise ValueError("Invalid operation ID.")
        with self._lock:
            item = self._pending.get(operation_id)
            if item is None:
                raise ValueError("Unknown controlled action.")
            try:
                if (
                    type(approved) is not bool
                    or approver.agent_name != "human"
                    or not self._same(
                        approver.organization_id, item.context.organization_id
                    )
                    or not (
                        type(approver.user_id) is UUID
                        or type(approver.user_id) is int
                        and approver.user_id > 0
                    )
                ):
                    raise PermissionError("Invalid approval authority.")
                self.permissions.authorize(approver, Permission("actions", "approve"))
            except (PermissionError, TypeError, AttributeError):
                self._event(
                    "action.approval_rejected",
                    operation_id,
                    item.context,
                    item.agent_name,
                    item.definition,
                )
                # Do not return another tenant's action details to the rejected caller.
                raise PermissionError("Approval not authorized.") from None
            if item.terminal is not None or item.approval != "pending":
                raise ValueError("Action is not awaiting approval.")
            decision = "approved" if approved else "denied"
            if not self._event(
                f"action.{decision}",
                operation_id,
                item.context,
                item.agent_name,
                item.definition,
                approver.user_id,
            ):
                item.terminal = self._outcome(item, "audit_failed")
                return item.terminal
            item.approval = decision
            if not approved:
                item.terminal = self._outcome(item, "denied")
                return item.terminal
            return self._outcome(item, "approved")

    def execute(
        self,
        operation_id: UUID,
        *,
        agent: Agent,
        context: AgentContext,
        authorization: AuthorizationContext,
    ) -> ControlledActionResult:
        identity = self._identity(context, agent.name)
        if type(operation_id) is not UUID:
            raise ValueError("Invalid operation ID.")
        with self._lock:
            item = self._pending.get(operation_id)
            if item is None or (
                self._identity(item.context, item.agent_name) != identity
                or item.agent_name != agent.name
            ):
                self._event("action.access_rejected", operation_id, context, agent.name)
                raise PermissionError("Controlled action not accessible.")
            try:
                self._authorize(item.definition, agent, context, authorization)
            except (PermissionError, TypeError, AttributeError):
                logged = self._event(
                    "action.unauthorized",
                    operation_id,
                    context,
                    agent.name,
                    item.definition,
                )
                return self._outcome(item, "unauthorized" if logged else "audit_failed")
            if item.terminal is not None:
                if not self._event(
                    "action.replay_blocked",
                    operation_id,
                    context,
                    agent.name,
                    item.definition,
                ):
                    return self._outcome(item, "audit_failed")
                return item.terminal
            # Policy is re-evaluated in case trusted policy was made more restrictive.
            requirement = self.policy.evaluate(
                item.definition.name, item.definition.risk
            )
            if requirement.approval_required and item.approval != "approved":
                logged = self._event(
                    "action.execution_blocked",
                    operation_id,
                    context,
                    agent.name,
                    item.definition,
                )
                return self._outcome(
                    item, "approval_required" if logged else "audit_failed"
                )
            if item.approval not in ("automatic", "approved"):
                return self._outcome(item, "approval_required")
            return self._run(item)

    def _run(self, item: _Pending) -> ControlledActionResult:
        definition = item.definition
        if not self._event(
            "action.execution_started",
            item.operation_id,
            item.context,
            item.agent_name,
            definition,
        ):
            item.terminal = self._outcome(item, "audit_failed")
            return item.terminal
        # Claim before invoking callbacks; reentrant/concurrent calls cannot execute twice.
        item.terminal = self._outcome(item, "indeterminate")
        request = ActionRequest(
            definition.name,
            True,
            definition.tool_name,
            json.loads(item.parameters_json),
        )
        execution_error = None
        try:
            raw = self.executor.execute(request, context=item.context)
            successful = isinstance(raw, ActionResult) and (
                raw.action_name == definition.name
                and raw.tool_name == definition.tool_name
                and raw.success is True
            )
        except (RuntimeError, ValueError, TypeError, KeyError, OSError) as exc:
            successful = False
            execution_error = type(exc).__name__
        execution = ActionResult(definition.name, definition.tool_name, {}, successful)
        execution_logged = self._event(
            "action.executed" if successful else "action.execution_failed",
            item.operation_id,
            item.context,
            item.agent_name,
            definition,
            error_type=execution_error,
        )
        # Every execution attempt reaches the existing verifier, even after an audit failure.
        verification_error = None
        try:
            checked = self.verifier.verify(
                execution,
                context=item.context,
                parameters=json.loads(item.parameters_json),
            )
            verified = (
                isinstance(checked, VerificationResult)
                and checked.action_name == definition.name
                and checked.verified is True
            )
        except (RuntimeError, ValueError, TypeError, KeyError, OSError) as exc:
            verified = False
            verification_error = type(exc).__name__
        verification = VerificationResult(
            definition.name,
            successful and verified,
            "Verification passed."
            if successful and verified
            else "Verification failed.",
        )
        verification_logged = self._event(
            "action.verified"
            if verification.verified
            else "action.verification_failed",
            item.operation_id,
            item.context,
            item.agent_name,
            definition,
            error_type=verification_error,
        )
        status = (
            "succeeded"
            if verification.verified
            else "verification_failed"
            if successful
            else "execution_failed"
        )
        if not execution_logged or not verification_logged:
            status = "audit_failed"
        item.terminal = self._outcome(item, status, execution, verification)
        return item.terminal
