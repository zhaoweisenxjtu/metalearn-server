"""Shared test fixtures — temp database for DAO tests."""

import os
import pytest
from pathlib import Path

from engine.db.database import init_db

TEST_API_KEY = "ml_test_key_00112233445566778899aabbccdd"


@pytest.fixture(autouse=True)
def reset_db():
    """每测试用例前创建临时数据库。"""
    old_db = os.environ.get("META_LEARN_DB")
    old_bootstrap = os.environ.get("META_LEARN_BOOTSTRAP_KEY")
    tmp_dir = Path(__file__).parent / "_test_"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_db = str(tmp_dir / "test.db")

    # Clean any leftover from previous failed runs
    for f in tmp_dir.glob("test.db*"):
        f.unlink()

    os.environ["META_LEARN_DB"] = tmp_db
    os.environ["META_LEARN_BOOTSTRAP_KEY"] = TEST_API_KEY

    init_db(force=True)
    yield

    # Cleanup test db files
    for f in tmp_dir.glob("test.db*"):
        f.unlink()

    # Restore env
    if old_db:
        os.environ["META_LEARN_DB"] = old_db
    else:
        os.environ.pop("META_LEARN_DB", None)
    if old_bootstrap:
        os.environ["META_LEARN_BOOTSTRAP_KEY"] = old_bootstrap
    else:
        os.environ.pop("META_LEARN_BOOTSTRAP_KEY", None)
