"""Tests for Multi-Track Scheduler."""

import pytest
from datetime import date, timedelta
from engine.db import dao_user, dao_track, dao_node
from engine.scheduler.multi_track import MultiTrackScheduler


@pytest.fixture
def setup():
    u = dao_user.create_user("sched_tester", "Tester")
    t1 = dao_track.create_track(u["id"], "数学", "exam", priority=5)
    t2 = dao_track.create_track(u["id"], "英语", "exam", priority=3)
    n1 = dao_node.add_node(t1["id"], "微积分", importance=5)
    n2 = dao_node.add_node(t1["id"], "线性代数", importance=4)
    n3 = dao_node.add_node(t2["id"], "词汇", importance=3)
    # Make some due
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    dao_node.update_node(n1["id"], next_review=yesterday)
    dao_node.update_node(n3["id"], next_review=yesterday)
    return {"user_id": u["id"], "track_ids": [t1["id"], t2["id"]]}


class TestMultiTrackScheduler:
    def test_get_schedule_basic(self, setup):
        s = MultiTrackScheduler().get_schedule(setup["user_id"])
        assert s["date"] == date.today().isoformat()
        assert len(s["tracks"]) > 0

    def test_get_schedule_with_time(self, setup):
        s = MultiTrackScheduler().get_schedule(setup["user_id"], total_minutes=120)
        total = sum(t["allocation_minutes"] for t in s["tracks"])
        assert total <= 120

    def test_get_schedule_priority_ordering(self, setup):
        s = MultiTrackScheduler().get_schedule(setup["user_id"])
        priorities = [t["priority"] for t in s["tracks"]]
        assert priorities == sorted(priorities, reverse=True)

    def test_get_schedule_identifies_due(self, setup):
        s = MultiTrackScheduler().get_schedule(setup["user_id"])
        for t in s["tracks"]:
            if t["name"] == "数学":
                assert t["due_reviews"] > 0

    def test_get_schedule_activities(self, setup):
        s = MultiTrackScheduler().get_schedule(setup["user_id"])
        for t in s["tracks"]:
            if t["activities"]:
                act_types = {a["type"] for a in t["activities"]}
                assert act_types.issubset({"review", "new_learning"})

    def test_get_schedule_no_user(self):
        s = MultiTrackScheduler().get_schedule(999)
        assert s.get("tracks") == []

    def test_get_schedule_empty_user(self):
        u = dao_user.create_user("empty", "Empty")
        s = MultiTrackScheduler().get_schedule(u["id"])
        assert s.get("tracks") == []
