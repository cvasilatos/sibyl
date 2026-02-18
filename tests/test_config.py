"""Tests for the configuration module."""

import os
import pytest
from sibyl.config import SibylConfig, LLMConfig


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
    assert config.max_tokens == 4000


def test_sibyl_config_from_env(monkeypatch):
    """Test creating Sibyl config from environment variables."""
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")

    config = SibylConfig.from_env()

    assert config.ollama is not None
    assert config.ollama.model == "llama3.2"
    assert config.ollama.api_url == "http://localhost:11434"


def test_ollama_config_defaults(monkeypatch):
    """Test Ollama configuration with default values."""
    monkeypatch.setenv("OLLAMA_MODEL", "mistral")

    config = SibylConfig.from_env()

    assert config.ollama is not None
    assert config.ollama.model == "mistral"
    assert config.ollama.api_url == "http://localhost:11434"  # Default
    assert config.ollama.temperature == 0.7  # Default
    assert config.ollama.max_tokens == 4000  # Default


def test_get_active_providers(monkeypatch):
    """Test getting list of active providers."""
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")

    config = SibylConfig.from_env()
    providers = config.get_active_providers()

    assert "ollama" in providers
    assert len(providers) == 1


def test_no_providers_configured():
    """Test when no providers are configured."""
    config = SibylConfig()
    providers = config.get_active_providers()

    assert len(providers) == 0
