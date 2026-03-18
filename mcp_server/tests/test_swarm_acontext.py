import pytest
from mcp_server.swarm.acontext_adapter import AcontextAdapter


@pytest.fixture
def acontext():
    return AcontextAdapter(
        irc_host="localhost", port=6667, channel="#test-channel", nickname="TestAgent"
    )


@pytest.mark.asyncio
async def test_broadcast_intent_local_lock(acontext):
    await acontext.broadcast_intent("agent1", "worker_abc", "data_entry")
    assert not acontext.is_worker_available("worker_abc")
    assert acontext.get_lock_owner("worker_abc") == "agent1"


@pytest.mark.asyncio
async def test_broadcast_release_local_lock(acontext):
    await acontext.broadcast_intent("agent1", "worker_abc", "data_entry")
    assert not acontext.is_worker_available("worker_abc")
    await acontext.broadcast_release("worker_abc")
    assert acontext.is_worker_available("worker_abc")


def test_parse_message_sets_lock(acontext):
    msg = (
        ":Agent2!user@host PRIVMSG #test-channel :!intent Agent2 worker_xyz moderation"
    )
    acontext.channel = "#test-channel"
    acontext._parse_message(msg)
    assert not acontext.is_worker_available("worker_xyz")
    assert acontext.get_lock_owner("worker_xyz") == "Agent2"


def test_parse_release_removes_lock(acontext):
    msg_intent = (
        ":Agent2!user@host PRIVMSG #test-channel :!intent Agent2 worker_xyz moderation"
    )
    msg_release = ":Agent2!user@host PRIVMSG #test-channel :!release worker_xyz"
    acontext._parse_message(msg_intent)
    assert not acontext.is_worker_available("worker_xyz")
    acontext._parse_message(msg_release)
    assert acontext.is_worker_available("worker_xyz")
