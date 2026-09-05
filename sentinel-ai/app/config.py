"""
SentinelAI Configuration Module
Production-ready configuration management with environment variable support.
"""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ProviderConfig:
    """Configuration for a single AI provider."""
    name: str
    api_key_env: str
    base_url: str
    models: List[str]
    cost_per_1k_tokens: float
    avg_latency_ms: float
    reliability_score: float  # 0.0 to 1.0
    max_requests_per_minute: int
    enabled: bool = True


@dataclass
class SentinelConfig:
    """Main configuration for SentinelAI."""
    # API Settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Health Monitoring
    health_check_interval_seconds: int = 10
    health_check_timeout_seconds: int = 5
    consecutive_failures_threshold: int = 3
    recovery_threshold: int = 2
    
    # Failover Settings
    failover_enabled: bool = True
    max_retries: int = 3
    retry_delay_ms: int = 100
    fallback_timeout_ms: int = 5000
    
    # Cost Optimization
    cost_optimization_enabled: bool = True
    max_cost_per_request: float = 0.10  # USD
    
    # Security
    api_key_header: str = "X-API-Key"
    required_api_keys: List[str] = field(default_factory=list)
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    
    # Guardrails
    max_tokens_limit: int = 8192
    
    # Demo Mode
    demo_mode: bool = True
    
    # Providers (will be populated from environment)
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    
    @classmethod
    def load_from_env(cls) -> 'SentinelConfig':
        """Load configuration from environment variables."""
        config = cls(
            host=os.getenv("SENTINEL_HOST", "0.0.0.0"),
            port=int(os.getenv("SENTINEL_PORT", "8000")),
            debug=os.getenv("SENTINEL_DEBUG", "false").lower() == "true",
            health_check_interval_seconds=int(os.getenv("HEALTH_CHECK_INTERVAL", "10")),
            consecutive_failures_threshold=int(os.getenv("FAILURE_THRESHOLD", "3")),
            max_cost_per_request=float(os.getenv("MAX_COST_PER_REQUEST", "0.10")),
            demo_mode=os.getenv("DEMO_MODE", "true").lower() == "true",
        )
        
        # Load API keys for authentication if needed
        api_keys_str = os.getenv("REQUIRED_API_KEYS", "")
        if api_keys_str:
            config.required_api_keys = [key.strip() for key in api_keys_str.split(",")]
        
        # Initialize default providers
        config.providers = cls._load_providers_from_env()
        
        return config
    
    @staticmethod
    def _load_providers_from_env() -> Dict[str, ProviderConfig]:
        """Load provider configurations from environment variables."""
        providers = {}
        
        # OpenAI Configuration
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            providers["openai"] = ProviderConfig(
                name="OpenAI",
                api_key_env="OPENAI_API_KEY",
                base_url="https://api.openai.com/v1",
                models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
                cost_per_1k_tokens=0.015,  # Average for gpt-4o
                avg_latency_ms=800,
                reliability_score=0.98,
                max_requests_per_minute=500,
                enabled=True
            )
        
        # Anthropic Configuration
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if anthropic_key:
            providers["anthropic"] = ProviderConfig(
                name="Anthropic",
                api_key_env="ANTHROPIC_API_KEY",
                base_url="https://api.anthropic.com/v1",
                models=["claude-sonnet-4-20260514", "claude-opus-4-20260514"],
                cost_per_1k_tokens=0.015,
                avg_latency_ms=900,
                reliability_score=0.97,
                max_requests_per_minute=400,
                enabled=True
            )
        
        # Google AI Configuration
        google_key = os.getenv("GOOGLE_API_KEY", "")
        if google_key:
            providers["google"] = ProviderConfig(
                name="Google",
                api_key_env="GOOGLE_API_KEY",
                base_url="https://generativelanguage.googleapis.com/v1beta",
                models=["gemini-2.5-pro", "gemini-2.5-flash"],
                cost_per_1k_tokens=0.0075,
                avg_latency_ms=700,
                reliability_score=0.96,
                max_requests_per_minute=600,
                enabled=True
            )
        
        # Groq Configuration (for speed)
        groq_key = os.getenv("GROQ_API_KEY", "")
        if groq_key:
            providers["groq"] = ProviderConfig(
                name="Groq",
                api_key_env="GROQ_API_KEY",
                base_url="https://api.groq.com/openai/v1",
                models=["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
                cost_per_1k_tokens=0.0007,
                avg_latency_ms=200,
                reliability_score=0.95,
                max_requests_per_minute=1000,
                enabled=True
            )
        
        # Local/Ollama Configuration (fallback)
        if os.getenv("ENABLE_LOCAL_MODELS", "false").lower() == "true":
            providers["local"] = ProviderConfig(
                name="Local",
                api_key_env="",
                base_url=os.getenv("LOCAL_MODEL_URL", "http://localhost:11434/v1"),
                models=["llama3.1", "mistral"],
                cost_per_1k_tokens=0.0,
                avg_latency_ms=1500,
                reliability_score=0.90,
                max_requests_per_minute=100,
                enabled=True
            )
        
        # If no providers configured, add mock providers for testing
        if not providers:
            # Add all major providers with mock keys for demo/development
            providers["openai"] = ProviderConfig(
                name="OpenAI",
                api_key_env="OPENAI_API_KEY",
                base_url="https://api.openai.com/v1",
                models=["gpt-4o", "gpt-4o-mini"],
                cost_per_1k_tokens=0.015,
                avg_latency_ms=800,
                reliability_score=0.98,
                max_requests_per_minute=500,
                enabled=True
            )
            providers["anthropic"] = ProviderConfig(
                name="Anthropic",
                api_key_env="ANTHROPIC_API_KEY",
                base_url="https://api.anthropic.com/v1",
                models=["claude-sonnet-4-20260514", "claude-opus-4-20260514"],
                cost_per_1k_tokens=0.015,
                avg_latency_ms=900,
                reliability_score=0.97,
                max_requests_per_minute=400,
                enabled=True
            )
            providers["google"] = ProviderConfig(
                name="Google",
                api_key_env="GOOGLE_API_KEY",
                base_url="https://generativelanguage.googleapis.com/v1beta",
                models=["gemini-2.5-pro", "gemini-2.5-flash"],
                cost_per_1k_tokens=0.0075,
                avg_latency_ms=700,
                reliability_score=0.96,
                max_requests_per_minute=600,
                enabled=True
            )
            providers["groq"] = ProviderConfig(
                name="Groq",
                api_key_env="GROQ_API_KEY",
                base_url="https://api.groq.com/openai/v1",
                models=["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
                cost_per_1k_tokens=0.0007,
                avg_latency_ms=200,
                reliability_score=0.95,
                max_requests_per_minute=1000,
                enabled=True
            )
        
        return providers
    
    def get_enabled_providers(self) -> List[ProviderConfig]:
        """Get list of enabled providers sorted by reliability score."""
        return sorted(
            [p for p in self.providers.values() if p.enabled],
            key=lambda x: x.reliability_score,
            reverse=True
        )
    
    def get_best_provider_for_cost(self) -> Optional[ProviderConfig]:
        """Get the cheapest enabled provider."""
        enabled = self.get_enabled_providers()
        if not enabled:
            return None
        return min(enabled, key=lambda x: x.cost_per_1k_tokens)
    
    def get_best_provider_for_speed(self) -> Optional[ProviderConfig]:
        """Get the fastest enabled provider."""
        enabled = self.get_enabled_providers()
        if not enabled:
            return None
        return min(enabled, key=lambda x: x.avg_latency_ms)
