"""Unit tests for API Key DAO."""
# conftest.py sets META_LEARN_BOOTSTRAP_KEY=ml_test_key_00112233445566778899aabbccdd

from engine.db.dao_api_key import create_key, validate_key, revoke_key, list_keys, get_key_count
from tests.conftest import TEST_API_KEY


class TestValidateKey:
    def test_bootstrap_key_is_valid(self):
        key = validate_key(TEST_API_KEY)
        assert key is not None
        assert key["is_admin"] == 1

    def test_invalid_key_returns_none(self):
        assert validate_key("nonexistent_key") is None

    def test_empty_key_returns_none(self):
        assert validate_key("") is None


class TestCreateKey:
    def test_create_and_validate(self):
        result = create_key("my key", is_admin=False)
        raw = result["key"]
        assert raw.startswith("ml_")
        assert result["key_prefix"] == raw[:12]
        assert result["is_admin"] is False

        key = validate_key(raw)
        assert key is not None
        assert key["is_admin"] == 0
        assert key["display_name"] == "my key"

    def test_create_admin_key(self):
        result = create_key("admin key", is_admin=True)
        key = validate_key(result["key"])
        assert key["is_admin"] == 1

    def test_create_key_with_user_id(self):
        from engine.db.dao_user import create_user
        user = create_user("keyuser")
        result = create_key("user bound", is_admin=False, user_id=user["id"])
        key = validate_key(result["key"])
        assert key["user_id"] == user["id"]

    def test_key_uniqueness(self):
        k1 = create_key("k1")
        k2 = create_key("k2")
        assert k1["key"] != k2["key"]


class TestRevokeKey:
    def test_revoke_active_key(self):
        result = create_key("to revoke")
        key_id = result["id"]
        raw = result["key"]

        assert validate_key(raw) is not None
        assert revoke_key(key_id) is True
        assert validate_key(raw) is None

    def test_revoke_already_revoked_returns_false(self):
        result = create_key("to revoke twice")
        revoke_key(result["id"])
        assert revoke_key(result["id"]) is False

    def test_revoke_nonexistent_returns_false(self):
        assert revoke_key(99999) is False


class TestListKeys:
    def test_list_active_only(self):
        k1 = create_key("active1")
        k2 = create_key("active2")
        revoke_key(k2["id"])

        keys = list_keys(include_inactive=False)
        ids = [k["id"] for k in keys]
        assert k1["id"] in ids  # bootstrap key also active
        assert k2["id"] not in ids

    def test_list_all_includes_revoked(self):
        k = create_key("temp")
        revoke_key(k["id"])

        all_keys = list_keys(include_inactive=True)
        revoked_ids = [k2["id"] for k2 in all_keys if not k2["active"]]
        assert k["id"] in revoked_ids

    def test_list_does_not_expose_hash(self):
        keys = list_keys()
        for k in keys:
            assert "key_hash" not in k


class TestGetKeyCount:
    def test_count_bootstrap_key(self):
        assert get_key_count() >= 1

    def test_count_after_create(self):
        before = get_key_count()
        create_key("count test")
        assert get_key_count() == before + 1

    def test_count_after_revoke(self):
        k = create_key("count revoke")
        before = get_key_count()
        revoke_key(k["id"])
        assert get_key_count() == before - 1
