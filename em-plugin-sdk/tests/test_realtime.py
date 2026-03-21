"""Tests for the realtime module — event types and room helpers."""

from em_plugin_sdk.realtime.event_types import (
    EventType,
    task_room,
    user_room,
    category_room,
    GLOBAL_ROOM,
)


class TestEventTypes:
    def test_task_events(self):
        assert EventType.TASK_CREATED == "TaskCreated"
        assert EventType.TASK_COMPLETED == "TaskCompleted"
        assert EventType.TASK_CANCELLED == "TaskCancelled"

    def test_submission_events(self):
        assert EventType.SUBMISSION_RECEIVED == "SubmissionReceived"
        assert EventType.SUBMISSION_APPROVED == "SubmissionApproved"
        assert EventType.SUBMISSION_REJECTED == "SubmissionRejected"

    def test_payment_events(self):
        assert EventType.PAYMENT_RELEASED == "PaymentReleased"
        assert EventType.PAYMENT_ESCROWED == "PaymentEscrowed"
        assert EventType.PAYMENT_FAILED == "PaymentFailed"

    def test_all_event_types_are_strings(self):
        attrs = [v for k, v in vars(EventType).items() if not k.startswith("_")]
        assert len(attrs) >= 20
        for attr in attrs:
            assert isinstance(attr, str)


class TestRoomHelpers:
    def test_task_room(self):
        assert task_room("abc-123") == "task:abc-123"

    def test_user_room(self):
        assert user_room("agent_42") == "user:agent_42"

    def test_category_room(self):
        assert category_room("physical_presence") == "category:physical_presence"

    def test_global_room(self):
        assert GLOBAL_ROOM == "global"


class TestWSClientImport:
    def test_can_import_event_client(self):
        """EMEventClient can be imported (websockets is installed in dev)."""
        from em_plugin_sdk.realtime import EMEventClient
        assert EMEventClient is not None

    def test_constructor_needs_no_args(self):
        """Client can be instantiated with defaults."""
        from em_plugin_sdk.realtime import EMEventClient
        client = EMEventClient()
        assert client.is_connected is False
