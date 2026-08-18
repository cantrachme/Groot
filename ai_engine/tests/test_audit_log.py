import unittest
from uuid import uuid4


class AuditEventTests(unittest.TestCase):

    def test_stores_audit_event_data(self):
        from ai_engine.app.audit import AuditEvent

        user_id = uuid4()
        organization_id = uuid4()

        event = AuditEvent(
            event_name="customer.deleted",
            user_id=user_id,
            organization_id=organization_id,
            agent_name="operations_agent",
        )

        self.assertEqual(
            event.event_name,
            "customer.deleted",
        )
        self.assertEqual(
            event.user_id,
            user_id,
        )
        self.assertEqual(
            event.organization_id,
            organization_id,
        )
        self.assertEqual(
            event.agent_name,
            "operations_agent",
        )


class AuditLogTests(unittest.TestCase):

    def test_records_event(self):
        from ai_engine.app.audit import (
            AuditEvent,
            AuditLog,
        )

        event = AuditEvent(
            event_name="customer.deleted",
            user_id=uuid4(),
            organization_id=uuid4(),
            agent_name="operations_agent",
        )

        audit_log = AuditLog()

        audit_log.record(event)

        self.assertEqual(
            audit_log.events,
            (event,),
        )

    def test_preserves_event_order(self):
        from ai_engine.app.audit import (
            AuditEvent,
            AuditLog,
        )

        first_event = AuditEvent(
            event_name="customer.read",
            user_id=uuid4(),
            organization_id=uuid4(),
            agent_name="operations_agent",
        )

        second_event = AuditEvent(
            event_name="customer.deleted",
            user_id=uuid4(),
            organization_id=uuid4(),
            agent_name="operations_agent",
        )

        audit_log = AuditLog()

        audit_log.record(first_event)
        audit_log.record(second_event)

        self.assertEqual(
            audit_log.events,
            (
                first_event,
                second_event,
            ),
        )


if __name__ == "__main__":
    unittest.main()
