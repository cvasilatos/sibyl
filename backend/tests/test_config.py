"""Tests for the configuration module."""

import pytest

from sibyl.config import LLMConfig, MAX_SCORE


def test_max_score_value():
    """Test that MAX_SCORE is a positive integer."""
    assert isinstance(MAX_SCORE, int)
    assert MAX_SCORE > 0


def test_max_score_is_five():
    """Test that MAX_SCORE equals 5."""
    assert MAX_SCORE == 5


def test_llm_config_creation():
    """Test creating an LLM configuration with required fields."""
    config = LLMConfig(name="TestLLM")
    assert config.name == "TestLLM"


def test_llm_config_defaults():
    """Test LLM configuration default values."""
    config = LLMConfig(name="TestLLM")
    assert config.temperature == 0.7
    assert config.max_tokens == 300000


def test_llm_config_custom_values():
    """Test LLM configuration with custom temperature and max_tokens."""
    config = LLMConfig(name="CustomLLM", temperature=0.5, max_tokens=2000)
    assert config.name == "CustomLLM"
    assert config.temperature == 0.5
    assert config.max_tokens == 2000


def test_llm_config_name_required():
    """Test that LLM configuration requires a name field."""
    with pytest.raises(Exception):
        LLMConfig()  # type: ignore[call-arg]


def test_llm_config_temperature_range():
    """Test LLM configuration accepts valid temperature values."""
    config = LLMConfig(name="t", temperature=0.0)
    assert config.temperature == 0.0
    config2 = LLMConfig(name="t", temperature=1.0)
    assert config2.temperature == 1.0


def test_llm_config_max_tokens_custom():
    """Test LLM configuration with a custom max_tokens value."""
    config = LLMConfig(name="t", max_tokens=8000)
    assert config.max_tokens == 8000
