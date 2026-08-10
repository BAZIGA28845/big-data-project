import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(str(Path(__file__).resolve().parent.parent))

from ai_assistant import is_safe_select, ask


def test_is_safe_select_accepts_normal_select():
    assert is_safe_select("SELECT * FROM clean_gdacs WHERE year = 2020") is True


def test_is_safe_select_rejects_drop():
    assert is_safe_select("DROP TABLE clean_gdacs") is False


def test_is_safe_select_rejects_delete():
    assert is_safe_select("DELETE FROM clean_gdacs WHERE year = 2020") is False


def test_is_safe_select_rejects_update():
    assert is_safe_select("UPDATE clean_gdacs SET alert_level = 'Red'") is False


@patch("ai_assistant.question_to_sql")
def test_ask_handles_no_query_response(mock_q2sql):
    mock_q2sql.return_value = "NO_QUERY"
    result = ask("What's the weather tomorrow?")
    assert "can't answer" in result.lower() or "don't think" in result.lower()


@patch("ai_assistant.question_to_sql")
def test_ask_handles_unsafe_sql_without_crashing(mock_q2sql):
    mock_q2sql.return_value = "DROP TABLE clean_gdacs"
    result = ask("Delete everything")
    assert isinstance(result, str)
    assert "can't" in result.lower() or "sorry" in result.lower()


@patch("ai_assistant.question_to_sql")
def test_ask_handles_sql_generation_failure_without_crashing(mock_q2sql):
    mock_q2sql.side_effect = Exception("API error")
    result = ask("Any question")
    assert isinstance(result, str)
    assert "trouble" in result.lower() or "sorry" in result.lower()