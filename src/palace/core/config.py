"""
Palace Framework Configuration Module

This module defines all configuration settings for the Palace framework using
pydantic-settings for environment variable loading and validation.

Configuration is organized into logical groups:
    - OllamaConfig: Ollama cloud connection settings
    - ModelConfig: Model assignments for each agent type
    - MemoryConfig: Memory store configuration (Zep/SQLite)
    - DatabaseConfig: Framework state database
    - APIConfig: REST API settings
    - CLIConfig: Command-line interface settings
    - LoggingConfig: Logging configuration
    - ProjectsConfig: Projects storage settings
    - SecurityConfig: Authentication and security settings

Usage:
    from palace.core.config import settings

    print(settings.ollama.base_url)
    print(settings.model.orchestrator)
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaConfig(BaseSettings):
    """Ollama Cloud connection configuration."""

    model_config = SettingsConfigDict(
        env_prefix="OLLAMA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for Ollama API",
    )
    api_key: str | None = Field(
        default=None,
        description="API key for Ollama Cloud authentication",
    )
    timeout: int = Field(
        default=300,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed requests",
    )


class ModelConfig(BaseSettings):
    """Model assignments for each agent type."""

    model_config = SettingsConfigDict(
        env_prefix="MODEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Orchestrator and DevOps use qwen3.5:cloud
    orchestrator: str = Field(
        default="qwen3.5:cloud",
        description="Model for orchestrator agent (Ollama Cloud)",
    )
    devops: str = Field(
        default="qwen3.5:cloud",
        description="Model for DevOps agent (Ollama Cloud)",
    )

    # Development agents use qwen3-coder-next:cloud
    backend: str = Field(
        default="qwen3-coder-next:cloud",
        description="Model for backend development agent (Ollama Cloud)",
    )
    frontend: str = Field(
        default="qwen3-coder-next:cloud",
        description="Model for frontend development agent (Ollama Cloud)",
    )
    infra: str = Field(
        default="qwen3-coder-next:cloud",
        description="Model for infrastructure agent (Ollama Cloud)",
    )

    # DBA uses deepseek-v3.2:cloud
    dba: str = Field(
        default="deepseek-v3.2:cloud",
        description="Model for DBA agent (Ollama Cloud)",
    )

    # QA uses gemma4:31b-cloud
    qa: str = Field(
        default="gemma4:31b-cloud",
        description="Model for QA agent (Ollama Cloud)",
    )

    # Architecture and Review use mistral-large-3:675b-cloud
    designer: str = Field(
        default="mistral-large-3:675b-cloud",
        description="Model for designer agent (Ollama Cloud)",
    )
    reviewer: str = Field(
        default="mistral-large-3:675b-cloud",
        description="Model for reviewer agent (Ollama Cloud)",
    )

    # Embedding model for vector memory
    embedding: str = Field(
        default="nomic-embed-text",
        description="Model for generating embeddings",
    )

    def get_model_for_agent(self, agent_type: str) -> str:
        """Get the model assigned to a specific agent type.

        Args:
            agent_type: The type of agent (e.g., 'backend', 'frontend', 'dba')

        Returns:
            The model name assigned to that agent type

        Raises:
            ValueError: If the agent type is not recognized
        """
        model_mapping = {
            "orchestrator": self.orchestrator,
            "devops": self.devops,
            "backend": self.backend,
            "frontend": self.frontend,
            "infra": self.infra,
            "dba": self.dba,
            "qa": self.qa,
            "designer": self.designer,
            "reviewer": self.reviewer,
        }
        agent_type_lower = agent_type.lower()
        if agent_type_lower not in model_mapping:
            raise ValueError(
                f"Unknown agent type: {agent_type}. Valid types: {list(model_mapping.keys())}"
            )
        return model_mapping[agent_type_lower]


class MemoryConfig(BaseSettings):
    """Memory store configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MEMORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    store_type: Literal["zep", "sqlite", "chroma"] = Field(
        default="zep",
        description="Type of memory store to use",
    )
    local_memory_path: str = Field(
        default="./data/memory.db",
        description="Path for local SQLite memory store",
    )
    zep_api_url: str = Field(
        default="http://localhost:8000",
        description="Zep API URL",
    )
    zep_api_key: str | None = Field(
        default=None,
        description="Zep API key for authentication",
    )
    collection_name: str = Field(
        default="palace_memory",
        description="Collection name for vector store",
    )
    embedding_dimension: int = Field(
        default=1536,
        description="Dimension of embedding vectors",
    )
    chunk_size: int = Field(
        default=1000,
        description="Size of text chunks for embedding",
    )
    chunk_overlap: int = Field(
        default=200,
        description="Overlap between chunks",
    )


class DatabaseConfig(BaseSettings):
    """Framework state database configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/palace.db",
        description="Database connection URL for framework state",
    )
    database_echo: bool = Field(
        default=False,
        description="Echo SQL queries for debugging",
    )
    database_pool_size: int = Field(
        default=5,
        description="Connection pool size",
    )


class APIConfig(BaseSettings):
    """REST API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(
        default="0.0.0.0",
        description="API server host",
    )
    port: int = Field(
        default=8000,
        description="API server port",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins",
    )
    api_prefix: str = Field(
        default="/api/v1",
        description="API route prefix",
    )
    workers: int = Field(
        default=1,
        description="Number of worker processes",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


class CLIConfig(BaseSettings):
    """Command-line interface configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CLI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    default_project: str = Field(
        default="default",
        description="Default project ID when not specified",
    )
    history_file: str = Field(
        default="./data/cli_history.json",
        description="Path to CLI history file",
    )
    output_format: Literal["text", "json", "markdown"] = Field(
        default="text",
        description="Output format for CLI commands",
    )
    color_output: bool = Field(
        default=True,
        description="Enable colored output",
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose output",
    )


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Log level",
    )
    format: Literal["json", "text"] = Field(
        default="json",
        description="Log format",
    )
    file_path: str | None = Field(
        default=None,
        description="Optional log file path",
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10 MB
        description="Maximum log file size in bytes",
    )
    backup_count: int = Field(
        default=5,
        description="Number of backup log files",
    )


class ProjectsConfig(BaseSettings):
    """Projects storage configuration."""

    model_config = SettingsConfigDict(
        env_prefix="PROJECTS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_path: str = Field(
        default="./projects",
        description="Base path for project storage",
    )
    max_projects: int = Field(
        default=100,
        description="Maximum number of projects",
    )
    auto_create: bool = Field(
        default=True,
        description="Automatically create project directories",
    )


class SecurityConfig(BaseSettings):
    """Security and authentication configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for JWT signing",
    )
    api_key_header: str = Field(
        default="X-API-Key",
        description="Header name for API key authentication",
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes",
    )
    require_authentication: bool = Field(
        default=False,
        description="Require authentication for API endpoints",
    )


class Settings(BaseSettings):
    """
    Main settings class that aggregates all configuration groups.

    This class provides a single entry point for all configuration settings,
    loading from environment variables with sensible defaults.

    Usage:
        from palace.core.config import settings

        # Access configuration
        print(settings.ollama.base_url)
        print(settings.model.backend)
        print(settings.api.host)

        # Get model for specific agent
        model = settings.model.get_model_for_agent("backend")
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Configuration groups
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    cli: CLIConfig = Field(default_factory=CLIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    projects: ProjectsConfig = Field(default_factory=ProjectsConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    # Framework metadata
    app_name: str = Field(
        default="Palace Framework",
        description="Application name",
    )
    app_version: str = Field(
        default="0.1.0",
        description="Application version",
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    This function returns a singleton Settings instance, caching it
    for the lifetime of the application.

    Returns:
        Settings: The application settings instance
    """
    return Settings()


# Global settings instance
settings = get_settings()
