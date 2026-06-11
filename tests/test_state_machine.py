"""Tests for state machine (pure function)."""

import pytest
from engine.workflow.state_machine import (
    is_valid_transition, get_allowed_transitions, get_state_label,
    get_next_recommended, get_guarded_next, STATES,
)


class TestStateMachine:
    def test_valid_transitions(self):
        """Check documented transitions."""
        assert is_valid_transition("init", "diagnosis") is True
        assert is_valid_transition("diagnosis", "teaching") is True
        assert is_valid_transition("teaching", "assessment") is True
        assert is_valid_transition("assessment", "practice") is True
        assert is_valid_transition("assessment", "teaching") is True
        assert is_valid_transition("assessment", "completed") is True
        assert is_valid_transition("practice", "assessment") is True

    def test_invalid_transitions(self):
        """Check invalid transitions."""
        assert is_valid_transition("init", "teaching") is False
        assert is_valid_transition("init", "completed") is False
        assert is_valid_transition("teaching", "practice") is False
        assert is_valid_transition("completed", "init") is False

    def test_completed_has_no_outgoing(self):
        """Completed state should have no outgoing transitions."""
        assert get_allowed_transitions("completed") == []

    def test_all_states_have_labels(self):
        """Every state should have a Chinese label."""
        for s in STATES:
            label = get_state_label(s)
            assert len(label) > 0
            assert label != s  # should not fall back to raw state name

    def test_unknown_state_label(self):
        """Unknown state should return raw name."""
        assert get_state_label("unknown") == "unknown"

    def test_get_next_recommended_init(self):
        """Init should recommend diagnosis."""
        result = get_next_recommended({"current_state": "init"})
        assert result["next_state"] == "diagnosis"
        assert result["can_transition"] is True

    def test_get_next_recommended_completed(self):
        """Completed should stay completed."""
        result = get_next_recommended({"current_state": "completed"})
        assert result["next_state"] == "completed"
        assert result["can_transition"] is False

    def test_get_guarded_next_assessment_all_l4(self):
        """All nodes L4+ in exam track should recommend completed."""
        result = get_guarded_next(
            {"current_state": "assessment", "target_type": "exam"},
            [{"status": "active", "current_level": 4}, {"status": "active", "current_level": 5}],
        )
        assert result["next_state"] == "completed"

    def test_get_guarded_next_assessment_all_l3_but_below_l4(self):
        """All nodes L3+ but not all L4+ should recommend practice."""
        result = get_guarded_next(
            {"current_state": "assessment", "target_type": "applied"},
            [{"status": "active", "current_level": 3}, {"status": "active", "current_level": 4}],
        )
        assert result["next_state"] == "practice"

    def test_get_guarded_next_assessment_has_below_l3(self):
        """Some nodes below L3 should recommend teaching."""
        result = get_guarded_next(
            {"current_state": "assessment"},
            [{"status": "active", "current_level": 2}, {"status": "active", "current_level": 4}],
        )
        assert result["next_state"] == "teaching"

    def test_get_guarded_next_no_nodes(self):
        """No nodes should recommend teaching."""
        result = get_guarded_next(
            {"current_state": "assessment"},
            [],
        )
        assert result["next_state"] == "teaching"

    def test_get_guarded_next_practice(self):
        """Practice should always recommend assessment."""
        result = get_guarded_next({"current_state": "practice"}, [])
        assert result["next_state"] == "assessment"

    def test_get_guarded_next_falls_back_to_recommended(self):
        """Non-assessment/practice states should fall back to get_next_recommended."""
        result = get_guarded_next({"current_state": "init"}, [])
        assert result["next_state"] == "diagnosis"
