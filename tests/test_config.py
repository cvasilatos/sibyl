"""Tests for the configuration module."""

import os
import pytest
from sibyl.config import SibylConfig, LLMConfig


def test_llm_config_creation():
    """Test creating an LLM configuration."""
    config = LLMConfig(
        name="TestLLM",
        api_key="test_key",
        model="test-model",
        temperature=0.5,
        max_tokens=2000,
    )

    assert config.name == "TestLLM"
    assert config.api_key == "test_key"
    assert config.model == "test-model"
    assert config.temperature == 0.5
    assert config.max_tokens == 2000


def test_llm_config_defaults():
    """Test LLM configuration default values."""
    config = LLMConfig(name="TestLLM", api_key="test_key", model="test-model")

    assert config.temperature == 0.7
    assert config.max_tokens == 4000


def test_sibyl_config_from_env(monkeypatch):
    """Test creating Sibyl config from environment variables."""
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")

    config = SibylConfig.from_env()

    assert config.openai is not None
    assert config.openai.api_key == "test_openai_key"
    assert config.openai.model == "gpt-4-test"
    assert config.anthropic is not None
    assert config.anthropic.api_key == "test_anthropic_key"
    assert config.google is None


def test_get_active_providers(monkeypatch):
    """Test getting list of active providers."""
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test_key")

    config = SibylConfig.from_env()
    providers = config.get_active_providers()

    assert "openai" in providers
    assert "google" in providers
    assert "anthropic" not in providers
    assert len(providers) == 2


def test_no_providers_configured():
    """Test when no providers are configured."""
    config = SibylConfig()
    providers = config.get_active_providers()

    assert len(providers) == 0
