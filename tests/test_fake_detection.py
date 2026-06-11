"""Tests for FakeDetector (pure function)."""

import pytest
from engine.core.fake_detection import FakeDetector


class TestFakeDetector:
    def test_no_signals(self):
        """No signals should return risk 'none'."""
        result = FakeDetector.assess({})
        assert result["risk_level"] == "none"
        assert result["total_signals"] == 0
        assert result["details"] == []

    def test_all_false(self):
        """All signals false should return risk 'none'."""
        signals = {name: False for name in FakeDetector.SIGNALS}
        result = FakeDetector.assess(signals)
        assert result["risk_level"] == "none"
        assert result["total_signals"] == 0

    def test_single_signal_low_risk(self):
        """1 signal should be low risk."""
        signals = {"can_not_restate": True}
        result = FakeDetector.assess(signals)
        assert result["risk_level"] == "low"
        assert result["total_signals"] == 1
        assert result["details"][0]["signal"] == "can_not_restate"

    def test_two_to_three_signals_medium_risk(self):
        """2-3 signals should be medium risk."""
        signals = {"can_not_restate": True, "term_barrier": True}
        result = FakeDetector.assess(signals)
        assert result["risk_level"] == "medium"
        assert result["total_signals"] == 2

        signals["analogy_failure"] = True
        result = FakeDetector.assess(signals)
        assert result["risk_level"] == "medium"

    def test_four_or_more_signals_high_risk(self):
        """4+ signals should be high risk."""
        signals = {name: True for name in list(FakeDetector.SIGNALS)[:4]}
        result = FakeDetector.assess(signals)
        assert result["risk_level"] == "high"

    def test_all_signals_high_risk(self):
        """All 10 signals should be high risk."""
        signals = {name: True for name in FakeDetector.SIGNALS}
        result = FakeDetector.assess(signals)
        assert result["risk_level"] == "high"
        assert result["total_signals"] == 10

    def test_signals_have_descriptions(self):
        """Each active signal should have a description."""
        signals = {"can_not_restate": True, "boundary_blur": True}
        result = FakeDetector.assess(signals)
        for detail in result["details"]:
            assert "description" in detail
            assert len(detail["description"]) > 0

    def test_unknown_signals_ignored(self):
        """Signals not in the known set should be ignored."""
        signals = {"can_not_restate": True, "made_up_signal": True}
        result = FakeDetector.assess(signals)
        assert result["total_signals"] == 1

    def test_get_probing_questions_existing(self):
        """Known signal should return questions."""
        questions = FakeDetector.get_probing_questions("can_not_restate")
        assert len(questions) > 0
        assert "合上材料" in questions[0]

    def test_get_probing_questions_unknown(self):
        """Unknown signal should return fallback question."""
        questions = FakeDetector.get_probing_questions("nonexistent")
        assert questions == ["请详细解释你的理解"]

    def test_quick_check_summary_none(self):
        """None risk should return appropriate summary."""
        s = FakeDetector.quick_check_summary({"risk_level": "none", "total_signals": 0, "details": []})
        assert "无" in s

    def test_quick_check_summary_high(self):
        """High risk summary should mention all signals."""
        details = [{"signal": "x", "description": "test desc"}]
        s = FakeDetector.quick_check_summary({"risk_level": "high", "total_signals": 1, "details": details})
        assert "高" in s
