"""
Universal Hiring Matrix — party matching gate.

Validates the single source of truth (`api.party`) that every apply/accept path
shares, so the 3x3 matrix {human,agent,robot} x {human,agent,robot} (+ 'any')
behaves identically across REST and MCP. See
MASTER_PLAN_UNIVERSAL_HIRING_MATRIX.md (Phase 2 + 3).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.party import can_execute, party_required_label
from models import PartyType, party_type_from_agent_type

PARTIES = [p.value for p in PartyType]  # human, agent, robot


@pytest.mark.core
class TestCanExecute:
    @pytest.mark.parametrize("party", PARTIES)
    def test_any_target_open_to_all(self, party):
        assert can_execute(party, "any") is True

    @pytest.mark.parametrize("party", PARTIES)
    def test_unset_target_open_to_all(self, party):
        assert can_execute(party, None) is True
        assert can_execute(party, "") is True

    @pytest.mark.parametrize("party", PARTIES)
    def test_same_party_allowed(self, party):
        assert can_execute(party, party) is True

    @pytest.mark.parametrize("party", PARTIES)
    @pytest.mark.parametrize("target", PARTIES)
    def test_full_matrix(self, party, target):
        # Exactly the diagonal is allowed for specific targets.
        assert can_execute(party, target) is (party == target)

    def test_unknown_executor_party_rejected_for_specific_target(self):
        assert can_execute(None, "human") is False
        assert can_execute("alien", "agent") is False


@pytest.mark.core
class TestPartyLabel:
    def test_any(self):
        assert party_required_label("any") == "any party"
        assert party_required_label(None) == "any party"

    @pytest.mark.parametrize("target", PARTIES)
    def test_specific(self, target):
        assert party_required_label(target) == f"{target} executors"


@pytest.mark.core
class TestAgentTypeMapping:
    @pytest.mark.parametrize(
        "agent_type,expected",
        [
            ("human", "human"),
            ("ai", "agent"),
            ("agent", "agent"),
            ("organization", "agent"),
            ("robot", "robot"),
            (None, "human"),
            ("unknown", "human"),
        ],
    )
    def test_party_type_from_agent_type(self, agent_type, expected):
        assert party_type_from_agent_type(agent_type) == expected
