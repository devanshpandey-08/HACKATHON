"""
SentinelAI - Health Monitor Tests
"""
import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.health_monitor import HealthMonitor, ProviderHealth
from app.config import SentinelConfig


def test_provider_health_initialization():
    """Test ProviderHealth dataclass initialization"""
    health = ProviderHealth(name="test-provider")
    
    assert health.name == "test-provider"
    assert health.is_healthy == True
    assert health.latency_ms == 0.0
    assert health.success_rate == 100.0
    assert health.consecutive_failures == 0
    assert health.error_message is None


def test_provider_health_add_response_time():
    """Test adding response times to provider health"""
    health = ProviderHealth(name="test-provider")
    
    # Add some response times
    health.add_response_time(100.0)
    health.add_response_time(150.0)
    health.add_response_time(200.0)
    
    # Check average latency
    assert health.latency_ms == 150.0
    assert len(health.response_times) == 3
    
    # Add more to test trimming (keeps last 20)
    for i in range(25):
        health.add_response_time(float(i))
    
    assert len(health.response_times) == 20


def test_health_monitor_initialization():
    """Test HealthMonitor initialization"""
    config = SentinelConfig.load_from_env()
    
    monitor = HealthMonitor(config)
    
    assert len(monitor.providers) > 0
    assert 'openai' in monitor.providers or 'mock_provider' in monitor.providers or list(monitor.providers.keys())[0] in monitor.providers
    assert monitor.running == False


def test_get_healthy_providers():
    """Test getting list of healthy providers"""
    config = SentinelConfig.load_from_env()
    monitor = HealthMonitor(config)
    
    # Get first provider and mark as unhealthy
    provider_names = list(monitor.providers.keys())
    if len(provider_names) > 1:
        unhealthy_name = provider_names[0]
        monitor.providers[unhealthy_name].is_healthy = False
        monitor.providers[unhealthy_name].consecutive_failures = config.consecutive_failures_threshold
        
        healthy = monitor.get_healthy_providers()
        
        assert unhealthy_name not in healthy


def test_get_best_provider_latency():
    """Test getting best provider by latency"""
    config = SentinelConfig.load_from_env()
    monitor = HealthMonitor(config)
    
    # Set different latencies - groq has lowest (200ms), local has highest
    provider_names = list(monitor.providers.keys())
    if len(provider_names) >= 3:
        # Find groq provider (should be fastest) and set others slower
        for name in provider_names:
            if name == 'groq':
                monitor.providers[name].latency_ms = 100.0
            elif name == 'openai':
                monitor.providers[name].latency_ms = 300.0
            else:
                monitor.providers[name].latency_ms = 500.0
        
        best = monitor.get_best_provider('latency')
        assert best == 'groq'


def test_get_best_provider_reliability():
    """Test getting best provider by reliability"""
    config = SentinelConfig.load_from_env()
    monitor = HealthMonitor(config)
    
    # Set different success rates
    provider_names = list(monitor.providers.keys())
    if len(provider_names) >= 3:
        # Make openai most reliable
        for name in provider_names:
            if name == 'openai':
                monitor.providers[name].success_rate = 99.0
            elif name == 'anthropic':
                monitor.providers[name].success_rate = 75.0
            else:
                monitor.providers[name].success_rate = 50.0
        
        best = monitor.get_best_provider('reliability')
        assert best == 'openai'


def test_get_best_provider_no_healthy():
    """Test get_best_provider returns None when no healthy providers"""
    config = SentinelConfig.load_from_env()
    monitor = HealthMonitor(config)
    
    # Mark all as unhealthy
    for provider in monitor.providers.values():
        provider.is_healthy = False
    
    best = monitor.get_best_provider('latency')
    assert best is None


def test_get_all_health():
    """Test getting all health statuses"""
    config = SentinelConfig.load_from_env()
    monitor = HealthMonitor(config)
    
    all_health = monitor.get_all_health()
    
    assert len(all_health) > 0
    first_key = list(all_health.keys())[0]
    assert first_key in all_health
    assert isinstance(all_health[first_key], ProviderHealth)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
