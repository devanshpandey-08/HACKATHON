"""
SentinelAI - Core Configuration
"""
from pydantic_settings import BaseSettings
from typing import List, Optional


class ProviderConfig(BaseSettings):
    name: str
    api_key_env: str
    base_url: str
    models: List[str]
    priority: int = 1
    cost_per_1k_tokens: float = 0.0
    avg_latency_ms: float = 0.0


class SentinelConfig(BaseSettings):
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Redis Settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # PostgreSQL Settings
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "sentinel"
    db_user: str = "postgres"
    db_password: str = "postgres"
    
    # Health Check Settings
    health_check_interval_seconds: int = 10
    health_check_timeout_seconds: int = 5
    failure_threshold: int = 3
    
    # Fallback Settings
    max_retries: int = 3
    retry_delay_seconds: float = 0.5
    
    # Guardrails
    max_tokens_limit: int = 8192
    allowed_models: Optional[List[str]] = None
    
    # Demo Mode (for hackathon)
    demo_mode: bool = True
    
    class Config:
        env_file = ".env"


# Default provider configurations
DEFAULT_PROVIDERS = [
    ProviderConfig(
        name="openai",
        api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1",
        models=["gpt-6", "gpt-6-turbo", "gpt-5"],
        priority=1,
        cost_per_1k_tokens=0.03,
        avg_latency_ms=500
    ),
    ProviderConfig(
        name="anthropic",
        api_key_env="ANTHROPIC_API_KEY",
        base_url="https://api.anthropic.com/v1",
        models=["claude-opus-5", "claude-sonnet-5", "claude-3.5-sonnet"],
        priority=2,
        cost_per_1k_tokens=0.045,
        avg_latency_ms=600
    ),
    ProviderConfig(
        name="grok",
        api_key_env="GROK_API_KEY",
        base_url="https://api.x.ai/v1",
        models=["grok-4.6", "grok-4"],
        priority=3,
        cost_per_1k_tokens=0.025,
        avg_latency_ms=450
    ),
    ProviderConfig(
        name="local",
        api_key_env="",
        base_url="http://localhost:8080/v1",
        models=["llama-3-70b", "mixtral-8x22b"],
        priority=4,
        cost_per_1k_tokens=0.0,
        avg_latency_ms=200
    )
]
