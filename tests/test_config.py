"""
Tests for the Palace Framework configuration module.

This module tests the configuration loading, validation, and access patterns
for all configuration groups.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from palace.core.config import (
    APIConfig,
    CLIConfig,
    DatabaseConfig,
    LoggingConfig,
    MemoryConfig,
    ModelConfig,
    OllamaConfig,
    ProjectsConfig,
    SecurityConfig,
    Settings,
    get_settings,
)


class TestOllamaConfig:
    """Tests for Ollama configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = OllamaConfig()
        assert config.base_url == "http://localhost:11434"
        assert config.api_key is None
        assert config.timeout == 300
        assert config.max_retries == 3

    def test_custom_values(self):
        """Test custom configuration values."""
        config = OllamaConfig(
            base_url="https://ollama.example.com",
            api_key="test-api-key",
            timeout=600,
            max_retries=5,
        )
        assert config.base_url == "https://ollama.example.com"
        assert config.api_key == "test-api-key"
        assert config.timeout == 600
        assert config.max_retries == 5

    def test_env_vars(self):
        """Test loading from environment variables."""
        with patch.dict(
            os.environ,
            {
                "OLLAMA_BASE_URL": "https://env-ollama.example.com",
                "OLLAMA_API_KEY": "env-api-key",
                "OLLAMA_TIMEOUT": "120",
            },
        ):
            config = OllamaConfig()
            assert config.base_url == "https://env-ollama.example.com"
            assert config.api_key == "env-api-key"
            assert config.timeout == 120


class TestModelConfig:
    """Tests for model configuration."""

    def test_default_values(self):
        """Test default model assignments."""
        config = ModelConfig()
        assert config.orchestrator == "qwen3.5:cloud"
        assert config.devops == "qwen3.5:cloud"
        assert config.backend == "qwen3-coder-next:cloud"
        assert config.frontend == "qwen3-coder-next:cloud"
        assert config.infra == "qwen3-coder-next:cloud"
        assert config.dba == "deepseek-v3.2:cloud"
        assert config.qa == "gemma4:31b-cloud"
        assert config.designer == "mistral-large-3:675b-cloud"
        assert config.reviewer == "mistral-large-3:675b-cloud"
        assert config.embedding == "nomic-embed-text"

    def test_get_model_for_agent(self):
        """Test getting model for specific agent."""
        config = ModelConfig()

        assert config.get_model_for_agent("backend") == "qwen3-coder-next:cloud"
        assert config.get_model_for_agent("frontend") == "qwen3-coder-next:cloud"
        assert config.get_model_for_agent("dba") == "deepseek-v3.2:cloud"
        assert config.get_model_for_agent("qa") == "gemma4:31b-cloud"
        assert config.get_model_for_agent("reviewer") == "mistral-large-3:675b-cloud"

    def test_get_model_for_unknown_agent(self):
        """Test getting model for unknown agent raises error."""
        config = ModelConfig()

        with pytest.raises(ValueError) as exc_info:
            config.get_model_for_agent("unknown_agent")

        assert "Unknown agent type" in str(exc_info.value)

    def test_custom_model_assignments(self):
        """Test custom model assignments."""
        config = ModelConfig(
            backend="custom-backend-model",
            frontend="custom-frontend-model",
        )
        assert config.backend == "custom-backend-model"
        assert config.frontend == "custom-frontend-model"


class TestMemoryConfig:
    """Tests for memory configuration."""

    def test_default_values(self):
        """Test default memory configuration."""
        config = MemoryConfig()
        assert config.store_type == "zep"
        assert config.local_memory_path == "./data/memory.db"
        assert config.zep_api_url == "http://localhost:8000"
        assert config.zep_api_key is None
        assert config.collection_name == "palace_memory"
        assert config.embedding_dimension == 1536
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200

    def test_store_types(self):
        """Test different store types."""
        for store_type in ["zep", "sqlite", "chroma"]:
            config = MemoryConfig(store_type=store_type)
            assert config.store_type == store_type

    def test_invalid_store_type(self):
        """Test invalid store type raises error."""
        with pytest.raises(ValidationError):
            MemoryConfig(store_type="invalid")


class TestAPIConfig:
    """Tests for API configuration."""

    def test_default_values(self):
        """Test default API configuration."""
        config = APIConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.debug is False
        assert config.cors_origins == ["*"]
        assert config.api_prefix == "/api/v1"
        assert config.workers == 1

    def test_cors_origins_parsing(self):
        """Test CORS origins parsing from string."""
        with patch.dict(
            os.environ, {"API_CORS_ORIGINS": "http://localhost:3000,http://localhost:8080"}
        ):
            config = APIConfig()
            assert config.cors_origins == ["http://localhost:3000", "http://localhost:8080"]

    def test_cors_origins_list(self):
        """Test CORS origins as list."""
        config = APIConfig(cors_origins=["http://localhost:3000"])
        assert config.cors_origins == ["http://localhost:3000"]


class TestCLIConfig:
    """Tests for CLI configuration."""

    def test_default_values(self):
        """Test default CLI configuration."""
        config = CLIConfig()
        assert config.default_project == "default"
        assert config.history_file == "./data/cli_history.json"
        assert config.output_format == "text"
        assert config.color_output is True
        assert config.verbose is False

    def test_output_format_validation(self):
        """Test output format validation."""
        for format_type in ["text", "json", "markdown"]:
            config = CLIConfig(output_format=format_type)
            assert config.output_format == format_type

    def test_invalid_output_format(self):
        """Test invalid output format raises error."""
        with pytest.raises(ValidationError):
            CLIConfig(output_format="invalid")


class TestLoggingConfig:
    """Tests for logging configuration."""

    def test_default_values(self):
        """Test default logging configuration."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.format == "json"
        assert config.file_path is None
        assert config.max_file_size == 10 * 1024 * 1024
        assert config.backup_count == 5

    def test_log_level_validation(self):
        """Test log level validation."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level

    def test_invalid_log_level(self):
        """Test invalid log level raises error."""
        with pytest.raises(ValidationError):
            LoggingConfig(level="INVALID")


class TestDatabaseConfig:
    """Tests for database configuration."""

    def test_default_values(self):
        """Test default database configuration."""
        config = DatabaseConfig()
        assert "sqlite" in config.database_url
        assert config.database_echo is False
        assert config.database_pool_size == 5

    def test_custom_database_url(self):
        """Test custom database URL."""
        config = DatabaseConfig(database_url="postgresql://user:pass@localhost/db")
        assert config.database_url == "postgresql://user:pass@localhost/db"


class TestProjectsConfig:
    """Tests for projects configuration."""

    def test_default_values(self):
        """Test default projects configuration."""
        config = ProjectsConfig()
        assert config.base_path == "./projects"
        assert config.max_projects == 100
        assert config.auto_create is True


class TestSecurityConfig:
    """Tests for security configuration."""

    def test_default_values(self):
        """Test default security configuration."""
        config = SecurityConfig()
        assert config.secret_key == "change-me-in-production"
        assert config.api_key_header == "X-API-Key"
        assert config.access_token_expire_minutes == 30
        assert config.require_authentication is False


class TestSettings:
    """Tests for main Settings class."""

    def test_default_settings(self):
        """Test default settings initialization."""
        settings = Settings()
        assert settings.app_name == "Palace Framework"
        assert settings.app_version == "0.1.0"
        assert settings.environment == "development"

    def test_nested_configs(self):
        """Test nested configuration groups."""
        settings = Settings()

        assert isinstance(settings.ollama, OllamaConfig)
        assert isinstance(settings.model, ModelConfig)
        assert isinstance(settings.memory, MemoryConfig)
        assert isinstance(settings.database, DatabaseConfig)
        assert isinstance(settings.api, APIConfig)
        assert isinstance(settings.cli, CLIConfig)
        assert isinstance(settings.logging, LoggingConfig)
        assert isinstance(settings.projects, ProjectsConfig)
        assert isinstance(settings.security, SecurityConfig)

    def test_environment_methods(self):
        """Test environment check methods."""
        settings = Settings(environment="development")
        assert settings.is_development() is True
        assert settings.is_production() is False

        settings = Settings(environment="production")
        assert settings.is_development() is False
        assert settings.is_production() is True

    def test_invalid_environment(self):
        """Test invalid environment raises error."""
        with pytest.raises(ValidationError):
            Settings(environment="invalid")

    def test_settings_caching(self):
        """Test that get_settings caches properly."""
        # Clear cache first
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2


class TestSettingsFromEnv:
    """Tests for loading settings from environment."""

    def test_load_from_env_file(self, tmp_path):
        """Test loading settings from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
OLLAMA_BASE_URL=https://test-ollama.example.com
MODEL_BACKEND=test-backend-model
API_PORT=9000
CLI_DEFAULT_PROJECT=test-project
"""
        )

        with patch.dict(os.environ, {"ENV_FILE": str(env_file)}):
            settings = Settings()
            assert settings.ollama.base_url == "https://test-ollama.example.com"
            assert settings.model.backend == "test-backend-model"

    def test_env_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(
            os.environ,
            {
                "API_PORT": "9999",
                "MODEL_QA": "test-qa-model",
                "LOG_LEVEL": "DEBUG",
            },
        ):
            settings = Settings()
            assert settings.api.port == 9999
            assert settings.model.qa == "test-qa-model"
            assert settings.logging.level == "DEBUG"


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_port_validation(self):
        """Test port number validation."""
        # Valid port
        config = APIConfig(port=8000)
        assert config.port == 8000

        # Port out of range should work (Pydantic doesn't validate by default)
        config = APIConfig(port=99999)
        assert config.port == 99999

    def test_timeout_validation(self):
        """Test timeout validation."""
        config = OllamaConfig(timeout=60)
        assert config.timeout == 60

    def test_chunk_size_validation(self):
        """Test chunk size validation."""
        config = MemoryConfig(chunk_size=500, chunk_overlap=100)
        assert config.chunk_size == 500
        assert config.chunk_overlap == 100
