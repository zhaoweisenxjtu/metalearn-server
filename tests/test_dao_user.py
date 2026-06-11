"""Tests for User DAO layer."""

import pytest
import sqlite3
from engine.db import dao_user
from engine.db import dao_track


class TestUserDAO:
    def test_create_user(self):
        u = dao_user.create_user("alice", "Alice")
        assert u["name"] == "alice"
        assert u["display_name"] == "Alice"
        assert u["id"] > 0

    def test_create_duplicate_name_fails(self):
        dao_user.create_user("alice", "Alice")
        with pytest.raises(sqlite3.IntegrityError):
            dao_user.create_user("alice", "Another")

    def test_get_user(self):
        u = dao_user.create_user("bob", "Bob")
        found = dao_user.get_user(u["id"])
        assert found is not None
        assert found["name"] == "bob"

    def test_get_user_not_found(self):
        assert dao_user.get_user(9999) is None

    def test_get_user_by_name(self):
        dao_user.create_user("carol", "Carol")
        found = dao_user.get_user_by_name("carol")
        assert found is not None
        assert found["display_name"] == "Carol"

    def test_list_users_empty(self):
        assert dao_user.list_users() == []

    def test_list_users(self):
        dao_user.create_user("a", "A")
        dao_user.create_user("b", "B")
        users = dao_user.list_users()
        assert len(users) == 2

    def test_update_user_display_name(self):
        u = dao_user.create_user("dave", "Dave")
        updated = dao_user.update_user(u["id"], display_name="David")
        assert updated["display_name"] == "David"

    def test_delete_user(self):
        u = dao_user.create_user("eve", "Eve")
        assert dao_user.delete_user(u["id"]) is True
        assert dao_user.get_user(u["id"]) is None

    def test_delete_user_not_found(self):
        assert dao_user.delete_user(9999) is False

    def test_cascade_delete(self):
        """Deleting a user should cascade-delete their tracks."""
        u = dao_user.create_user("frank", "Frank")
        dao_track.create_track(u["id"], "Test Track", "applied")
        dao_user.delete_user(u["id"])
        tracks = dao_track.list_tracks(u["id"])
        assert tracks == []
