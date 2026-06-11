"""Integration tests for HTTP API via TestClient."""

import pytest
from fastapi.testclient import TestClient
from adapters.http_api.server import app
from engine.db import dao_node

client = TestClient(app)
AUTH = {"Authorization": "Bearer ml_test_key_00112233445566778899aabbccdd"}


class TestHealth:
    def test_health(self):
        """Health endpoint is public (no auth)."""
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestAuth:
    def test_no_auth_returns_401(self):
        r = client.get("/api/v1/users")
        assert r.status_code == 401

    def test_bad_key_returns_401(self):
        r = client.get("/api/v1/users", headers={"Authorization": "Bearer bad_key"})
        assert r.status_code == 401

    def test_valid_key_succeeds(self):
        r = client.get("/api/v1/users", headers=AUTH)
        assert r.status_code == 200


class TestUsersAPI:
    def test_create_user(self):
        r = client.post("/api/v1/users", params={"name": "apialice", "display_name": "API Alice"}, headers=AUTH)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == "apialice"
        assert data["id"] > 0

    def test_list_users(self):
        client.post("/api/v1/users", params={"name": "u1"}, headers=AUTH)
        client.post("/api/v1/users", params={"name": "u2"}, headers=AUTH)
        r = client.get("/api/v1/users", headers=AUTH)
        assert r.status_code == 200
        assert len(r.json()) == 2


class TestTracksAPI:
    def test_create_track(self):
        uid = client.post("/api/v1/users", params={"name": "trackapi"}, headers=AUTH).json()["id"]
        r = client.post("/api/v1/tracks", params={"user_id": uid, "name": "AI", "type": "applied"}, headers=AUTH)
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "AI"

    def test_list_tracks(self):
        uid = client.post("/api/v1/users", params={"name": "tracklist"}, headers=AUTH).json()["id"]
        client.post("/api/v1/tracks", params={"user_id": uid, "name": "T1", "type": "exam"}, headers=AUTH)
        client.post("/api/v1/tracks", params={"user_id": uid, "name": "T2", "type": "interest"}, headers=AUTH)
        r = client.get("/api/v1/tracks", params={"user_id": uid}, headers=AUTH)
        assert len(r.json()) == 2


class TestReviewsAPI:
    def test_create_review(self):
        uid = client.post("/api/v1/users", params={"name": "revapi"}, headers=AUTH).json()["id"]
        tid = client.post("/api/v1/tracks", params={"user_id": uid, "name": "R", "type": "exam"}, headers=AUTH).json()["id"]
        nid = client.post("/api/v1/nodes", params={"track_id": tid, "name": "RN", "importance": 3}, headers=AUTH).json()["id"]
        r = client.post("/api/v1/reviews", json={"node_id": nid, "quality": 4}, headers=AUTH)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "interval_days" in data
        assert data["passed"] is True

    def test_review_due(self):
        from datetime import date, timedelta
        uid = client.post("/api/v1/users", params={"name": "dueapi"}, headers=AUTH).json()["id"]
        tid = client.post("/api/v1/tracks", params={"user_id": uid, "name": "D", "type": "exam"}, headers=AUTH).json()["id"]
        nid = client.post("/api/v1/nodes", params={"track_id": tid, "name": "DN", "importance": 3}, headers=AUTH).json()["id"]
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        dao_node.update_node(nid, next_review=yesterday)
        r = client.get("/api/v1/reviews/due", params={"user_id": uid}, headers=AUTH)
        assert r.status_code == 200
        assert len(r.json()) >= 1


class TestKnowledgeAPI:
    def test_knowledge_query(self):
        r = client.post("/api/v1/knowledge/query", json={"query": "记忆", "top_k": 2}, headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] > 0
        assert len(data["results"]) > 0

    def test_knowledge_sources(self):
        r = client.get("/api/v1/knowledge/sources", headers=AUTH)
        assert r.status_code == 200
        assert len(r.json()) > 0


class TestDashboardAPI:
    def test_dashboard(self):
        uid = client.post("/api/v1/users", params={"name": "dashapi"}, headers=AUTH).json()["id"]
        r = client.get("/api/v1/dashboard", params={"user_id": uid}, headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert "total_nodes" in data

    def test_schedule_today(self):
        uid = client.post("/api/v1/users", params={"name": "schedapi"}, headers=AUTH).json()["id"]
        r = client.get("/api/v1/schedule/today", params={"user_id": uid}, headers=AUTH)
        assert r.status_code == 200
