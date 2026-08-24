"""Tests for the separation between ephemeral run state and durable memory."""

from datetime import datetime, timezone

import pytest

from tests.lesson_loader import load_lesson_module

lesson = load_lesson_module(
    "state_and_memory_lesson",
    "fundamentals/08_state_and_memory/agent.py",
)


FIXED_TIME = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


def test_memory_survives_new_store_instance(tmp_path):
    path = tmp_path / "agent.memory.json"
    first = lesson.JsonMemoryStore(path)
    first.put("evidence_rule", "Require passing tests", "project", now=lambda: FIXED_TIME)

    second = lesson.JsonMemoryStore(path)
    records = second.all()

    assert len(records) == 1
    assert records[0].key == "evidence_rule"
    assert records[0].value == "Require passing tests"
    assert records[0].updated_at == FIXED_TIME.isoformat()


def test_put_updates_existing_key(tmp_path):
    store = lesson.JsonMemoryStore(tmp_path / "agent.memory.json")
    store.put("style", "verbose", "user", now=lambda: FIXED_TIME)
    store.put("style", "concise", "user", now=lambda: FIXED_TIME)

    assert [(record.key, record.value) for record in store.all()] == [
        ("style", "concise")
    ]


def test_search_retrieves_relevant_memory_only(tmp_path):
    store = lesson.JsonMemoryStore(tmp_path / "agent.memory.json")
    store.put("evidence_rule", "Require tests before completion", "project", now=lambda: FIXED_TIME)
    store.put("lunch", "Lunch is Thursday", "chat", now=lambda: FIXED_TIME)

    records = store.search("What evidence and tests prove completion?")

    assert [record.key for record in records] == ["evidence_rule"]


def test_corrupt_store_fails_explicitly(tmp_path):
    path = tmp_path / "agent.memory.json"
    path.write_text("not-json", encoding="utf-8")

    with pytest.raises(lesson.MemoryStoreError, match="Cannot load memory store"):
        lesson.JsonMemoryStore(path).all()


def test_run_state_is_explicit_and_ephemeral():
    state = lesson.AgentRunState(task="verify the change", run_id="run-1")
    state.record("tests_started")
    state.record("tests_passed")

    assert state.step == 2
    assert state.observations == ["tests_started", "tests_passed"]
