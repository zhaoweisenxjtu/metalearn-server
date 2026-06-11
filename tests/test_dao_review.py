"""Tests for Review DAO layer."""

import pytest
from engine.db import dao_user, dao_track, dao_node, dao_review


@pytest.fixture
def node():
    u = dao_user.create_user("review_tester", "Tester")
    t = dao_track.create_track(u["id"], "Physics", "exam")
    n = dao_node.add_node(t["id"], "牛顿定律", importance=5)
    dao_node.update_node(n["id"], ef=2.5, interval=0, repetitions=0)
    return n


class TestReviewDAO:
    def test_create_review(self, node):
        r = dao_review.create_review(node["id"], quality=4, ef_after=2.6, interval_after=6)
        assert r["node_id"] == node["id"]
        assert r["quality"] == 4
        assert r["id"] > 0

    def test_get_review_stats(self, node):
        dao_review.create_review(node["id"], 5, 2.6, 6)
        dao_review.create_review(node["id"], 4, 2.5, 10)
        stats = dao_review.get_review_stats(node["id"])
        assert stats["total_reviews"] == 2
        assert stats["avg_quality"] == 4.5
        assert stats["pass_rate"] == 1.0  # both >= 3

    def test_get_review_stats_no_reviews(self, node):
        stats = dao_review.get_review_stats(node["id"])
        assert stats["total_reviews"] == 0
        assert stats["avg_quality"] is None  # SQLite AVG of empty set = NULL

    def test_list_reviews(self, node):
        dao_review.create_review(node["id"], 3, 2.4, 3)
        dao_review.create_review(node["id"], 5, 2.6, 8)
        reviews = dao_review.list_reviews(node["id"])
        assert len(reviews) == 2

    def test_list_reviews_empty(self):
        assert dao_review.list_reviews(999) == []

    def test_create_review_invalid_quality_negative(self, node):
        with pytest.raises(Exception):
            dao_review.create_review(node["id"], -1, 2.5, 1)

    def test_create_review_invalid_quality_high(self, node):
        with pytest.raises(Exception):
            dao_review.create_review(node["id"], 6, 2.5, 1)
