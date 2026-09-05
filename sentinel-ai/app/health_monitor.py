"""
SentinelAI - Provider Health Monitor
Monitors all AI providers for availability, latency, and errors
"""
import asyncio
import time
import httpx
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProviderHealth:
    name: str
    is_healthy: bool = True
    latency_ms: float = 0.0
    success_rate: float = 100.0
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    error_message: Optional[str] = None
    response_times: List[float] = field(default_factory=list)
    
    def add_response_time(self, latency: float):
        self.response_times.append(latency)
        # Keep only last 20 measurements
        if len(self.response_times) > 20:
            self.response_times = self.response_times[-20:]
        self.latency_ms = sum(self.response_times) / len(self.response_times)


class HealthMonitor:
    def __init__(self, providers: List[Dict], config):
        self.providers = {p['name']: ProviderHealth(name=p['name']) for p in providers}
        self.config = config
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def check_provider(self, provider: Dict) -> ProviderHealth:
        """Check health of a single provider"""
        health = self.providers[provider['name']]
        start_time = time.time()
        
        try:
            # Simple health check endpoint or minimal API call
            async with httpx.AsyncClient(timeout=self.config.health_check_timeout_seconds) as client:
                # For demo, we'll simulate checks
                # In production, this would make actual API calls
                if self.config.demo_mode:
                    # Simulate realistic behavior
                    await asyncio.sleep(0.1)  # Simulated network delay
                    
                    # Simulate occasional failures for demo
                    import random
                    if provider['name'] == 'openai' and random.random() < 0.3:
                        raise Exception("Simulated OpenAI outage")
                
                else:
                    # Real health check implementation
                    api_key = getattr(self.config, provider.get('api_key_env', ''), '')
                    headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
                    
                    response = await client.get(
                        f"{provider['base_url']}/health",
                        headers=headers
                    )
                    response.raise_for_status()
                
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
            
            if health.consecutive_failures >= self.config.failure_threshold:
                logger.warning(f"Provider {provider['name']} marked unhealthy after {health.consecutive_failures} failures")
        
        health.last_check = datetime.now()
        return health
    
    async def run_health_checks(self):
        """Continuously monitor all providers"""
        while self.running:
            tasks = []
            for provider_name, provider_config in self.providers.items():
                # Get original provider config
                orig_config = next((p for p in DEFAULT_PROVIDERS if p.name == provider_name), None)
                if orig_config:
                    tasks.append(self.check_provider({
                        'name': provider_name,
                        'base_url': orig_config.base_url,
                        'api_key_env': orig_config.api_key_env
                    }))
            
            if tasks:
                await asyncio.gather(*tasks)
            
            await asyncio.sleep(self.config.health_check_interval_seconds)
    
    def start(self):
        """Start background health monitoring"""
        self.running = True
        self._task = asyncio.create_task(self.run_health_checks())
        logger.info("Health monitor started")
    
    def stop(self):
        """Stop health monitoring"""
        self.running = False
        if self._task:
            self._task.cancel()
        logger.info("Health monitor stopped")
    
    def get_healthy_providers(self) -> List[str]:
        """Get list of healthy provider names"""
        return [
            name for name, health in self.providers.items()
            if health.is_healthy and health.consecutive_failures < self.config.failure_threshold
        ]
    
    def get_best_provider(self, criteria: str = 'latency') -> Optional[str]:
        """Get best provider based on criteria: latency, cost, or reliability"""
        healthy = [
            (name, health) for name, health in self.providers.items()
            if health.is_healthy
        ]
        
        if not healthy:
            return None
        
        if criteria == 'latency':
            return min(healthy, key=lambda x: x[1].latency_ms)[0]
        elif criteria == 'reliability':
            return max(healthy, key=lambda x: x[1].success_rate)[0]
        else:
            # Default: balance of latency and reliability
            return min(healthy, key=lambda x: x[1].latency_ms / (x[1].success_rate + 1))[0]
    
    def get_all_health(self) -> Dict[str, ProviderHealth]:
        """Get health status of all providers"""
        return self.providers.copy()


# Import here to avoid circular imports
from app.config import DEFAULT_PROVIDERS
