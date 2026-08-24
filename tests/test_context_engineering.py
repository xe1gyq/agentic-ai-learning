"""Tests for transparent, bounded context selection."""

import pytest

from tests.lesson_loader import load_lesson_module


lesson = load_lesson_module(
    "context_engineering_lesson",
    "fundamentals/07_context_engineering/agent.py",
)


def test_required_context_is_kept_before_optional_context():
    items = [
        lesson.ContextItem("optional", "chat", "unrelated note", priority=0),
        lesson.ContextItem("policy", "system", "verify with tests", required=True),
    ]

    selection = lesson.select_context(items, "verify the change", max_chars=30)

    assert [item.key for item in selection.included] == ["policy"]
    assert [item.key for item in selection.excluded] == ["optional"]


def test_relevance_breaks_equal_priority_tie():
    items = [
        lesson.ContextItem("relevant", "tool", "cache latency evidence", priority=1),
        lesson.ContextItem("irrelevant", "chat", "team lunch schedule", priority=1),
    ]

    selection = lesson.select_context(items, "inspect cache latency", max_chars=22)

    assert [item.key for item in selection.included] == ["relevant"]


def test_duplicate_content_is_not_injected_twice():
    items = [
        lesson.ContextItem("new", "run", "tests passed", priority=5),
        lesson.ContextItem("old", "note", "  TESTS   PASSED  ", priority=1),
    ]

    selection = lesson.select_context(items, "tests", max_chars=100)

    assert len(selection.included) == 1
    assert selection.included[0].key == "new"
    assert selection.excluded[0].key == "old"


def test_required_context_cannot_be_silently_truncated():
    item = lesson.ContextItem("policy", "system", "required policy", required=True)

    with pytest.raises(ValueError, match="Required context item"):
        lesson.select_context([item], "task", max_chars=4)


def test_rendered_context_preserves_provenance():
    item = lesson.ContextItem("metric", "measurement", "IPC = 2.1")

    rendered = lesson.render_context([item])

    assert '"key": "metric"' in rendered
    assert '"source": "measurement"' in rendered
    assert "IPC = 2.1" in rendered
