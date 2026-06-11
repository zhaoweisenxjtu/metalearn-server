"""Tests for SM-2 algorithm (pure function)."""

import pytest
from datetime import date, timedelta
from engine.core.sm2 import SM2Calculator


class TestSM2Calculator:
    def test_perfect_recall(self):
        """Perfect recall (quality=5) should advance interval."""
        result = SM2Calculator.compute(quality=5, ef=2.5, interval_days=0, repetitions=0)
        assert result["passed"] is True
        assert result["repetitions"] == 1
        assert result["interval_days"] == 1
        assert result["ef"] == 2.6  # 2.5 + (0.1 - 0*0.08) = 2.6
        assert result["next_review"] == (date.today() + timedelta(days=1)).isoformat()

    def test_good_recall(self):
        """Good recall (quality=4) on second repetition."""
        result = SM2Calculator.compute(quality=4, ef=2.5, interval_days=1, repetitions=1)
        assert result["passed"] is True
        assert result["repetitions"] == 2
        assert result["interval_days"] == 6
        assert result["ef"] == pytest.approx(2.5)  # 2.5 - 0.1 = 2.4 →...

    def test_third_repetition(self):
        """Third repetition should multiply interval by ef."""
        result = SM2Calculator.compute(quality=4, ef=2.5, interval_days=6, repetitions=2)
        assert result["passed"] is True
        assert result["repetitions"] == 3
        assert result["interval_days"] == 15  # round(6 * 2.5) = 15

    def test_failed_recall(self):
        """Failed recall (quality < 3) should reset."""
        result = SM2Calculator.compute(quality=1, ef=2.5, interval_days=10, repetitions=5)
        assert result["passed"] is False
        assert result["repetitions"] == 0
        assert result["interval_days"] == 1
        assert result["ef"] == pytest.approx(1.96, rel=0.01)

    def test_ef_never_below_min(self):
        """EF should never go below 1.3."""
        result = SM2Calculator.compute(quality=0, ef=2.5, interval_days=1, repetitions=0)
        assert result["ef"] >= 1.3

    def test_zero_quality_resets_ef_significantly(self):
        """Quality 0 should cause large ef drop."""
        result = SM2Calculator.compute(quality=0, ef=2.5, interval_days=1, repetitions=3)
        assert result["ef"] < 2.0

    def test_all_quality_levels_produce_valid_output(self):
        """All quality levels 0-5 should produce valid output."""
        for q in range(6):
            result = SM2Calculator.compute(quality=q, ef=2.5, interval_days=1, repetitions=1)
            assert result["ef"] >= 1.3
            assert result["interval_days"] >= 1
            assert result["repetitions"] >= 0
            assert "next_review" in result
            assert result["passed"] == (q >= 3)

    def test_invalid_quality_raises(self):
        """Quality outside 0-5 should raise ValueError."""
        with pytest.raises(ValueError):
            SM2Calculator.compute(quality=6, ef=2.5, interval_days=0, repetitions=0)
        with pytest.raises(ValueError):
            SM2Calculator.compute(quality=-1, ef=2.5, interval_days=0, repetitions=0)

    def test_custom_today(self):
        """Custom today date should be used for next_review."""
        custom = date(2026, 1, 1)
        result = SM2Calculator.compute(quality=5, ef=2.5, interval_days=0, repetitions=0, today=custom)
        assert result["next_review"] == "2026-01-02"

    def test_get_default_node(self):
        """Default node should have initial SM-2 parameters."""
        default = SM2Calculator.get_default_node()
        assert default["ef"] == 2.5
        assert default["interval"] == 0
        assert default["repetitions"] == 0
        assert default["next_review"] is None

    def test_consecutive_perfect_recalls(self):
        """Multiple perfect recalls should build up interval."""
        ef, interval, reps = 2.5, 0, 0
        results = []
        for _ in range(5):
            r = SM2Calculator.compute(quality=5, ef=ef, interval_days=interval, repetitions=reps)
            results.append(r)
            ef, interval, reps = r["ef"], r["interval_days"], r["repetitions"]

        assert results[0]["interval_days"] == 1
        assert results[1]["interval_days"] == 6
        assert results[2]["interval_days"] > 6  # after 3rd, interval * ef
        assert results[-1]["repetitions"] == 5
