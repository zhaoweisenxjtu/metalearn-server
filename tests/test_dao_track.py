"""Tests for Track DAO layer."""

import pytest
from engine.db import dao_user, dao_track


@pytest.fixture
def user():
    return dao_user.create_user("track_tester", "Tester")


class TestTrackDAO:
    def test_create_track(self, user):
        t = dao_track.create_track(user["id"], "数学", "exam", priority=4)
        assert t["name"] == "数学"
        assert t["target_type"] == "exam"
        assert t["priority"] == 4
        assert t["current_state"] == "init"

    def test_get_track(self, user):
        t = dao_track.create_track(user["id"], "物理", "applied")
        found = dao_track.get_track(t["id"])
        assert found is not None
        assert found["name"] == "物理"

    def test_get_track_not_found(self):
        assert dao_track.get_track(9999) is None

    def test_list_tracks_by_user(self, user):
        dao_track.create_track(user["id"], "T1", "exam")
        dao_track.create_track(user["id"], "T2", "interest")
        tracks = dao_track.list_tracks(user_id=user["id"])
        assert len(tracks) == 2

    def test_list_tracks_filter_status(self, user):
        dao_track.create_track(user["id"], "Active", "exam")
        t2 = dao_track.create_track(user["id"], "Paused", "interest")
        dao_track.update_track(t2["id"], status="paused")
        active = dao_track.list_tracks(user_id=user["id"], status="active")
        paused = dao_track.list_tracks(user_id=user["id"], status="paused")
        assert len(active) == 1
        assert len(paused) == 1

    def test_update_track_name(self, user):
        t = dao_track.create_track(user["id"], "Old", "exam")
        updated = dao_track.update_track(t["id"], name="New")
        assert updated["name"] == "New"

    def test_update_track_state(self, user):
        t = dao_track.create_track(user["id"], "FSM", "applied")
        updated = dao_track.update_track(t["id"], current_state="diagnosis")
        assert updated["current_state"] == "diagnosis"

    def test_list_no_tracks(self):
        assert dao_track.list_tracks(user_id=999) == []
