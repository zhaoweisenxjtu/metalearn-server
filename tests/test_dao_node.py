"""Tests for Knowledge Node DAO layer."""

import pytest
from engine.db import dao_user, dao_track, dao_node


@pytest.fixture
def track():
    u = dao_user.create_user("node_tester", "Tester")
    return dao_track.create_track(u["id"], "CS", "exam")


class TestNodeDAO:
    def test_add_node(self, track):
        n = dao_node.add_node(track["id"], "排序算法", importance=4, current_level=1)
        assert n["name"] == "排序算法"
        assert n["importance"] == 4
        assert n["current_level"] == 1
        assert n["track_id"] == track["id"]

    def test_get_node(self, track):
        n = dao_node.add_node(track["id"], "二分搜索")
        found = dao_node.get_node(n["id"])
        assert found is not None
        assert found["name"] == "二分搜索"

    def test_get_node_not_found(self):
        assert dao_node.get_node(9999) is None

    def test_list_nodes(self, track):
        dao_node.add_node(track["id"], "N1")
        dao_node.add_node(track["id"], "N2")
        nodes = dao_node.list_nodes(track_id=track["id"])
        assert len(nodes) == 2

    def test_list_nodes_empty(self):
        assert dao_node.list_nodes(track_id=999) == []

    def test_update_node_level(self, track):
        n = dao_node.add_node(track["id"], "动态规划")
        updated = dao_node.update_node(n["id"], current_level=3)
        assert updated["current_level"] == 3

    def test_update_node_sm2_fields(self, track):
        n = dao_node.add_node(track["id"], "SM2 Test")
        updated = dao_node.update_node(n["id"], ef=2.5, interval=7, repetitions=2, next_review="2026-07-01")
        assert updated["ef"] == 2.5
        assert updated["interval"] == 7
        assert updated["repetitions"] == 2
        assert updated["next_review"] == "2026-07-01"

    def test_delete_node(self, track):
        n = dao_node.add_node(track["id"], "ToDelete")
        assert dao_node.delete_node(n["id"]) is True
        assert dao_node.get_node(n["id"]) is None

    def test_delete_node_not_found(self):
        assert dao_node.delete_node(9999) is False

    def test_get_due_nodes(self, track):
        from datetime import date, timedelta
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        n1 = dao_node.add_node(track["id"], "Due")
        dao_node.update_node(n1["id"], next_review=yesterday)
        n2 = dao_node.add_node(track["id"], "NotDue")
        dao_node.update_node(n2["id"], next_review=tomorrow)
        due = dao_node.get_due_nodes(track["id"])
        ids = [n["id"] for n in due]
        assert n1["id"] in ids
        assert n2["id"] not in ids
