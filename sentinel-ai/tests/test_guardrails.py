"""
SentinelAI - Guardrails Tests
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import SentinelConfig


def test_config_defaults():
    """Test configuration default values"""
    config = SentinelConfig()
    
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.health_check_interval_seconds == 10
    assert config.consecutive_failures_threshold == 3
    assert config.max_retries == 3
    assert config.max_tokens_limit == 8192
    assert config.demo_mode == True


def test_max_tokens_guardrail():
    """Test max tokens limit enforcement"""
    config = SentinelConfig()
    
    # Valid token count
    assert 1024 <= config.max_tokens_limit
    
    # Limit is enforced in API (tested in test_orchestrator.py)
    assert config.max_tokens_limit == 8192


def test_demo_mode_enabled():
    """Test demo mode is enabled for hackathon"""
    config = SentinelConfig()
    assert config.demo_mode == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
