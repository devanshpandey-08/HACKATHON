"""
SentinelAI - Health Monitor Tests
"""
import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.health_monitor import HealthMonitor, ProviderHealth
from app.config import SentinelConfig, DEFAULT_PROVIDERS


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
    config = SentinelConfig()
    providers = [{'name': 'provider1'}, {'name': 'provider2'}]
    
    monitor = HealthMonitor(providers, config)
    
    assert len(monitor.providers) == 2
    assert 'provider1' in monitor.providers
    assert 'provider2' in monitor.providers
    assert monitor.running == False


def test_get_healthy_providers():
    """Test getting list of healthy providers"""
    config = SentinelConfig()
    providers = [
        {'name': 'healthy1'},
        {'name': 'healthy2'},
        {'name': 'unhealthy'}
    ]
    
    monitor = HealthMonitor(providers, config)
    
    # Mark one as unhealthy
    monitor.providers['unhealthy'].is_healthy = False
    monitor.providers['unhealthy'].consecutive_failures = config.failure_threshold
    
    healthy = monitor.get_healthy_providers()
    
    assert 'healthy1' in healthy
    assert 'healthy2' in healthy
    assert 'unhealthy' not in healthy


def test_get_best_provider_latency():
    """Test getting best provider by latency"""
    config = SentinelConfig()
    providers = [
        {'name': 'slow'},
        {'name': 'fast'},
        {'name': 'medium'}
    ]
    
    monitor = HealthMonitor(providers, config)
    
    # Set different latencies
    monitor.providers['slow'].latency_ms = 500.0
    monitor.providers['fast'].latency_ms = 100.0
    monitor.providers['medium'].latency_ms = 300.0
    
    best = monitor.get_best_provider('latency')
    assert best == 'fast'


def test_get_best_provider_reliability():
    """Test getting best provider by reliability"""
    config = SentinelConfig()
    providers = [
        {'name': 'unreliable'},
        {'name': 'reliable'},
        {'name': 'somewhat_reliable'}
    ]
    
    monitor = HealthMonitor(providers, config)
    
    # Set different success rates
    monitor.providers['unreliable'].success_rate = 50.0
    monitor.providers['reliable'].success_rate = 99.0
    monitor.providers['somewhat_reliable'].success_rate = 75.0
    
    best = monitor.get_best_provider('reliability')
    assert best == 'reliable'


def test_get_best_provider_no_healthy():
    """Test get_best_provider returns None when no healthy providers"""
    config = SentinelConfig()
    providers = [{'name': 'down1'}, {'name': 'down2'}]
    
    monitor = HealthMonitor(providers, config)
    
    # Mark all as unhealthy
    for provider in monitor.providers.values():
        provider.is_healthy = False
    
    best = monitor.get_best_provider('latency')
    assert best is None


def test_get_all_health():
    """Test getting all health statuses"""
    config = SentinelConfig()
    providers = [{'name': 'p1'}, {'name': 'p2'}]
    
    monitor = HealthMonitor(providers, config)
    
    all_health = monitor.get_all_health()
    
    assert len(all_health) == 2
    assert 'p1' in all_health
    assert 'p2' in all_health
    assert isinstance(all_health['p1'], ProviderHealth)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
