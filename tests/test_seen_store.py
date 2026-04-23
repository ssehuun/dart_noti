import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from dart_noti.store.seen import SeenStore


@pytest.fixture
def store(tmp_path: Path) -> SeenStore:
    return SeenStore(tmp_path / "seen.json", retention_days=90)


def test_initially_empty(store: SeenStore):
    assert not store.is_seen("abc")


def test_mark_and_check(store: SeenStore):
    store.mark_seen(["rcp001", "rcp002"])
    assert store.is_seen("rcp001")
    assert store.is_seen("rcp002")
    assert not store.is_seen("rcp003")


def test_filter_unseen(store: SeenStore):
    store.mark_seen(["rcp001"])
    result = store.filter_unseen(["rcp001", "rcp002", "rcp003"])
    assert result == ["rcp002", "rcp003"]


def test_persists_to_file(tmp_path: Path):
    path = tmp_path / "seen.json"
    s1 = SeenStore(path, retention_days=90)
    s1.mark_seen(["rcp001"])

    s2 = SeenStore(path, retention_days=90)
    assert s2.is_seen("rcp001")


def test_evict_old(tmp_path: Path):
    path = tmp_path / "seen.json"
    store = SeenStore(path, retention_days=30)

    old_time = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    new_time = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"old_rcp": old_time, "new_rcp": new_time}), encoding="utf-8"
    )

    store2 = SeenStore(path, retention_days=30)
    store2.evict_old()

    assert not store2.is_seen("old_rcp")
    assert store2.is_seen("new_rcp")


def test_corrupted_file_handled(tmp_path: Path):
    path = tmp_path / "seen.json"
    path.write_text("not valid json", encoding="utf-8")
    store = SeenStore(path, retention_days=90)
    assert not store.is_seen("anything")
