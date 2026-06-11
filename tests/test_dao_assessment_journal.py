"""Tests for Assessment and Journal DAO layer."""

import pytest
from engine.db import dao_user, dao_track, dao_node, dao_assessment, dao_journal


@pytest.fixture
def track():
    u = dao_user.create_user("aj_tester", "Tester")
    return dao_track.create_track(u["id"], "English", "exam")


class TestAssessmentDAO:
    def test_log_assessment(self, track):
        a = dao_assessment.log_assessment(
            user_id=track["user_id"],
            track_id=track["id"],
            level_after=3,
            duration_minutes=30,
            notes="基本掌握",
        )
        assert a["id"] > 0
        assert a["level_after"] == 3

    def test_log_assessment_with_node(self, track):
        u_id = track["user_id"]
        n = dao_node.add_node(track["id"], "语法")
        a = dao_assessment.log_assessment(
            user_id=u_id, track_id=track["id"],
            level_after=4, node_id=n["id"],
        )
        assert a["node_id"] == n["id"]

    def test_log_assessment_with_before(self, track):
        a = dao_assessment.log_assessment(
            user_id=track["user_id"],
            track_id=track["id"],
            level_before=2,
            level_after=4,
        )
        assert a["level_before"] == 2

    def test_list_assessments(self, track):
        u_id = track["user_id"]
        dao_assessment.log_assessment(u_id, track["id"], 3)
        dao_assessment.log_assessment(u_id, track["id"], 4)
        items = dao_assessment.list_assessments(track_id=track["id"])
        assert len(items) >= 2  # might share db with other tests via track_id

    def test_list_assessments_empty(self):
        assert dao_assessment.list_assessments(track_id=999) == []


class TestJournalDAO:
    def test_create_journal(self, track):
        j = dao_journal.create_journal(
            user_id=track["user_id"],
            date_str="2026-06-10",
            focus_minutes=120,
            diffuse_minutes=30,
            topics=["词汇", "语法"],
            methods=["间隔重复"],
        )
        assert j["date"] == "2026-06-10"
        assert j["focus_minutes"] == 120

    def test_get_journal_by_date(self, track):
        u_id = track["user_id"]
        dao_journal.create_journal(u_id, "2026-06-10", focus_minutes=90)
        j = dao_journal.get_journal_by_date(u_id, "2026-06-10")
        assert j is not None
        assert j["focus_minutes"] == 90

    def test_get_journal_not_found(self, track):
        j = dao_journal.get_journal_by_date(track["user_id"], "2099-01-01")
        assert j is None

    def test_list_journals(self, track):
        u_id = track["user_id"]
        dao_journal.create_journal(u_id, "2026-06-01")
        dao_journal.create_journal(u_id, "2026-06-02")
        items = dao_journal.list_journals(user_id=u_id)
        assert len(items) >= 2
