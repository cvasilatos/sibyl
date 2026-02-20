"""Tests for the configuration module."""

import os

import pytest

from sibyl.config import LLMConfig, SibylConfig


def test_llm_config_creation():
    """Test creating an LLM configuration."""
    config = LLMConfig(
        name="TestLLM",
        api_key=None,
        api_url="http://localhost:11434",
        model="test-model",
        temperature=0.5,
        max_tokens=2000,
    )

    assert config.name == "TestLLM"
    assert config.api_key is None
    assert config.api_url == "http://localhost:11434"
    assert config.model == "test-model"
    assert config.temperature == 0.5
    assert config.max_tokens == 2000


def test_llm_config_defaults():
    """Test LLM configuration default values."""
    config = LLMConfig(name="TestLLM", model="test-model")

    assert config.temperature == 0.7
    assert config.max_tokens == 8000


def test_sibyl_config_from_env(monkeypatch):
    """Test creating Sibyl config from environment variables."""
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")

    config = SibylConfig.from_env()

    assert isinstance(config, LLMConfig)
    assert config.model == "llama3.2"
    assert config.api_url == "http://localhost:11434"


def test_ollama_config_defaults(monkeypatch):
    """Test Ollama configuration with default values."""
    monkeypatch.setenv("OLLAMA_MODEL", "mistral")
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

    config = SibylConfig.from_env()

    assert isinstance(config, LLMConfig)
    assert config.model == "mistral"
    assert config.api_url == "http://localhost:11434"
    assert config.temperature == 0.7
    assert config.max_tokens == 8000


def test_from_env_returns_llm_config(monkeypatch):
    """Test that from_env returns an LLMConfig instance."""
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")

    config = SibylConfig.from_env()

    assert isinstance(config, LLMConfig)
    assert config.name == "Ollama"


def test_no_providers_configured():
    """Test that from_env raises KeyError when OLLAMA_MODEL is not set."""
    env_backup = os.environ.pop("OLLAMA_MODEL", None)
    try:
        with pytest.raises(KeyError):
            SibylConfig.from_env()
    finally:
        if env_backup is not None:
            os.environ["OLLAMA_MODEL"] = env_backup
