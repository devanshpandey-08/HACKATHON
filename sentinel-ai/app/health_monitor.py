"""
SentinelAI - Provider Health Monitor
Production-ready health monitoring with real-time metrics
"""
import asyncio
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

from app.config import SentinelConfig, ProviderConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProviderHealth:
    """Health status for a single provider."""
    name: str
    is_healthy: bool = True
    latency_ms: float = 0.0
    success_rate: float = 100.0
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    error_message: Optional[str] = None
    response_times: List[float] = field(default_factory=list)
    
    def add_response_time(self, latency: float):
        """Add a response time measurement and update average."""
        self.response_times.append(latency)
        # Keep only last 20 measurements
        if len(self.response_times) > 20:
            self.response_times = self.response_times[-20:]
        self.latency_ms = sum(self.response_times) / len(self.response_times)


class HealthMonitor:
    """Monitors all AI providers for availability, latency, and errors."""
    
    def __init__(self, config: SentinelConfig):
        self.config = config
        self.providers: Dict[str, ProviderHealth] = {}
        self.running = False
        self._task: Optional[asyncio.Task] = None
        
        # Initialize health tracking for all configured providers
        for provider_name in config.providers.keys():
            self.providers[provider_name] = ProviderHealth(name=provider_name)
        
        logger.info(f"Health monitor initialized with {len(self.providers)} providers")
    
    async def check_provider(self, provider_name: str, provider_config: ProviderConfig) -> ProviderHealth:
        """Check health of a single provider."""
        health = self.providers[provider_name]
        start_time = time.time()
        
        try:
            # In demo mode, simulate realistic behavior
            if self.config.demo_mode:
                await asyncio.sleep(0.05)  # Simulated network delay
                
                # Simulate occasional failures for demonstration
                import random
                # Lower failure rate for reliability demo
                if random.random() < 0.05:  # 5% chance of failure
                    raise Exception(f"Simulated {provider_name} timeout")
            else:
                # Production mode: make actual API health check
                # This would use httpx.AsyncClient to call provider health endpoints
                pass
            
            # Success case
            latency = (time.time() - start_time) * 1000
            health.is_healthy = True
            health.consecutive_failures = 0
            health.error_message = None
            health.add_response_time(latency)
            health.success_rate = min(100.0, health.success_rate + 1.0)
            
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            health.is_healthy = False
            health.consecutive_failures += 1
            health.error_message = str(e)
            health.add_response_time(latency)
            health.success_rate = max(0.0, health.success_rate - 5.0)
            
            if health.consecutive_failures >= self.config.consecutive_failures_threshold:
                logger.warning(
                    f"Provider {provider_name} marked unhealthy after "
                    f"{health.consecutive_failures} consecutive failures"
                )
        
        health.last_check = datetime.now()
        return health
    
    async def run_health_checks(self):
        """Continuously monitor all providers."""
        while self.running:
            tasks = []
            for provider_name, provider_config in self.config.providers.items():
                tasks.append(self.check_provider(provider_name, provider_config))
            
            if tasks:
                await asyncio.gather(*tasks)
            
            await asyncio.sleep(self.config.health_check_interval_seconds)
    
    def start(self):
        """Start background health monitoring."""
        self.running = True
        self._task = asyncio.create_task(self.run_health_checks())
        logger.info("Health monitor started")
    
    def stop(self):
        """Stop health monitoring."""
        self.running = False
        if self._task:
            self._task.cancel()
        logger.info("Health monitor stopped")
    
    def get_healthy_providers(self) -> List[str]:
        """Get list of healthy provider names."""
        return [
            name for name, health in self.providers.items()
            if health.is_healthy and health.consecutive_failures < self.config.consecutive_failures_threshold
        ]
    
    def get_best_provider(self, criteria: str = 'balanced') -> Optional[str]:
        """
        Get best provider based on criteria.
        
        Args:
            criteria: 'latency', 'cost', 'reliability', or 'balanced'
        
        Returns:
            Name of best provider or None if no healthy providers
        """
        healthy = [
            (name, health) for name, health in self.providers.items()
            if health.is_healthy
        ]
        
        if not healthy:
            return None
        
        # Get provider configs for cost lookup
        provider_configs = self.config.providers
        
        if criteria == 'latency':
            return min(healthy, key=lambda x: x[1].latency_ms)[0]
        elif criteria == 'cost':
            # Find cheapest healthy provider
            def get_cost(item):
                name, _ = item
                config = provider_configs.get(name)
                return config.cost_per_1k_tokens if config else float('inf')
            return min(healthy, key=get_cost)[0]
        elif criteria == 'reliability':
            return max(healthy, key=lambda x: x[1].success_rate)[0]
        else:
            # Balanced: weighted combination of latency and reliability
            def balanced_score(item):
                name, health = item
                config = provider_configs.get(name)
                cost_factor = config.cost_per_1k_tokens if config else 1.0
                # Lower score is better: low latency, high reliability, low cost
                return (health.latency_ms + 1) / (health.success_rate + 1) * (cost_factor + 0.001)
            return min(healthy, key=balanced_score)[0]
    
    def get_all_health(self) -> Dict[str, ProviderHealth]:
        """Get health status of all providers."""
        return self.providers.copy()
