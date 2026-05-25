from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE_PATH = PROJECT_ROOT / ".env"


class BaseConfigSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        extra="ignore",
        frozen=True,
        env_nested_delimiter="__",
        case_sensitive=False,
    )


class GitHubSettings(BaseConfigSettings):
    """GitHub Security Advisories API configuration"""

    model_config = SettingsConfigDict(
        env_prefix="GITHUB__",
        env_file=[".env", str(ENV_FILE_PATH)],
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    # API Configuration
    api_token: Optional[str] = None  # Increases rate limit 60 → 5000/hr
    base_url: str = "https://api.github.com"
    rate_limit_delay: float = 1.0  # Seconds between requests
    timeout_seconds: int = 30

    # Fetching Configuration
    max_results_per_run: int = 100
    default_severity_filter: str = "high,critical"  # Comma-separated
    default_ecosystem_filter: str = ""  # Empty = all ecosystems
    fetch_withdrawn: bool = False  # Skip withdrawn advisories

    # Pagination
    per_page: int = 100  # Max allowed by GitHub
    max_pages: int = 10  # Safety limit

    # Retry Configuration
    max_retries: int = 3
    retry_delay_base: float = 5.0  # Exponential backoff base


class PDFParserSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="PDF_PARSER__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    max_pages: int = 30
    max_file_size_mb: int = 20
    do_ocr: bool = False
    do_table_structure: bool = True


class ChunkingSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="CHUNKING__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    chunk_size: int = 600  # Target words per chunk
    overlap_size: int = 100  # Words to overlap between chunks
    min_chunk_size: int = 100  # Minimum words for a valid chunk
    section_based: bool = True  # Use section-based chunking when available


class OpenSearchSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="OPENSEARCH__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    host: str = "http://localhost:9200"
    index_name: str = "security-rag"
    chunk_index_suffix: str = "chunks"  # Creates single hybrid index: {index_name}-{suffix}
    max_text_size: int = 1000000

    # Vector search settings
    vector_dimension: int = 1024  # Jina embeddings dimension
    vector_space_type: str = "cosinesimil"  # cosinesimil, l2, innerproduct

    # Hybrid search settings
    rrf_pipeline_name: str = "hybrid-rrf-pipeline"
    hybrid_search_size_multiplier: int = 2  # Get k*multiplier for better recall


class LangfuseSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="LANGFUSE_",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    public_key: str = ""
    secret_key: str = ""
    base_url: str = "http://localhost:3001"  # Self-hosted Langfuse URL
    enabled: bool = False
    flush_at: int = 15  # Number of events before flushing
    flush_interval: float = 1.0  # Seconds between flushes
    max_retries: int = 3
    timeout: int = 30
    debug: bool = False


class RedisSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="REDIS__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    decode_responses: bool = True
    socket_timeout: int = 30
    socket_connect_timeout: int = 30

    # Cache settings
    ttl_hours: int = 6  # Cache TTL in hours


class TelegramSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="TELEGRAM__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    bot_token: str = ""
    enabled: bool = False


class UploadSettings(BaseConfigSettings):
    """Settings for user PDF uploads."""

    model_config = SettingsConfigDict(
        env_file=[".env", str(ENV_FILE_PATH)],
        env_prefix="UPLOAD__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    upload_directory: Path = Path("./data/user_uploads")
    max_upload_size_mb: int = 20
    allowed_mime_types: List[str] = ["application/pdf"]

    @field_validator("upload_directory")
    @classmethod
    def validate_upload_dir(cls, v: Path) -> Path:
        """Ensure upload directory is a Path object."""
        if isinstance(v, str):
            v = Path(v)
        # Directory creation happens in main.py lifespan
        return v


class Settings(BaseConfigSettings):
    app_version: str = "0.1.0"
    debug: bool = True
    environment: Literal["development", "staging", "production"] = "development"
    service_name: str = "rag-api"

    # Updated to use shared PostgreSQL database with .NET
    postgres_database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/rag_system"
    postgres_echo_sql: bool = False
    postgres_pool_size: int = 20
    postgres_max_overflow: int = 0

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    ollama_timeout: int = 300

    # Jina AI embeddings configuration
    jina_api_key: str = ""

    github: GitHubSettings = Field(default_factory=GitHubSettings)
    pdf_parser: PDFParserSettings = Field(default_factory=PDFParserSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    opensearch: OpenSearchSettings = Field(default_factory=OpenSearchSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    upload: UploadSettings = Field(default_factory=UploadSettings)

    @field_validator("postgres_database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not (v.startswith("postgresql://") or v.startswith("postgresql+psycopg2://")):
            raise ValueError("Database URL must start with 'postgresql://' or 'postgresql+psycopg2://'")
        return v


def get_settings() -> Settings:
    return Settings()
