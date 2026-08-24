"""
test_goal_logic.py — Tests for goal-checking logic.

The goal_met() function in loops/02_goal_based/agent.py is a pure function
that checks whether all required keywords appear in Claude's output.

We can't import loops/02_goal_based/agent.py directly because it has
module-level code that tries to call the Anthropic API immediately.

LESSON: This is why scripts should wrap their main logic in:
    if __name__ == "__main__":
        ...
That guard lets you import the file to test its functions
without triggering the script's side effects.

For now, we test the goal logic independently — same function, tested inline.
"""

import pytest

REQUIRED_KEYWORDS = ["reliable", "fast", "affordable"]


def goal_met(text: str) -> bool:
    """
    Return True when all required keywords appear in the output.
    (Extracted from loops/02_goal_based/agent.py for testing.)
    """
    text_lower = text.lower()
    missing = [kw for kw in REQUIRED_KEYWORDS if kw not in text_lower]
    return len(missing) == 0


class TestGoalMet:

    def test_all_keywords_present(self):
        text = "This service is reliable, fast, and affordable for everyone."
        assert goal_met(text) is True

    def test_missing_one_keyword(self):
        text = "This service is reliable and fast."
        assert goal_met(text) is False

    def test_missing_all_keywords(self):
        text = "This is a great service."
        assert goal_met(text) is False

    def test_case_insensitive(self):
        text = "RELIABLE and FAST and AFFORDABLE."
        assert goal_met(text) is True

    def test_mixed_case(self):
        text = "Reliable service that is Fast and Affordable."
        assert goal_met(text) is True

    def test_empty_string(self):
        assert goal_met("") is False

    def test_keyword_as_substring(self):
        # "unreliable" contains "reliable" — should still pass
        # (this tests how the current implementation handles substrings)
        text = "unreliable, fast, affordable"
        assert goal_met(text) is True  # "reliable" IS in "unreliable"

    def test_goal_not_met_returns_false(self):
        """Explicit: function returns bool, not a truthy string."""
        result = goal_met("missing keywords here")
        assert result is False
        assert isinstance(result, bool)


class TestGoalMetWithDifferentKeywords:
    """
    Shows how to parameterize goal logic for different keyword sets.
    pytest.mark.parametrize runs the same test with multiple inputs.
    """

    @pytest.mark.parametrize("text,expected", [
        ("fast and reliable and affordable", True),
        ("fast and reliable", False),
        ("", False),
        ("reliable FAST AFFORDABLE", True),
    ])
    def test_parametrized(self, text: str, expected: bool):
        assert goal_met(text) is expected
