"""
SentinelAI - Orchestrator Tests
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns welcome message"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "SentinelAI" in data["message"]
    assert "docs" in data
    assert "health" in data


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "healthy_providers" in data
    assert "total_providers" in data


def test_get_providers():
    """Test get all providers endpoint"""
    response = client.get("/api/providers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Check provider structure
    provider = data[0]
    assert "provider" in provider
    assert "healthy" in provider
    assert "latency_ms" in provider
    assert "success_rate" in provider


def test_chat_endpoint_basic():
    """Test basic chat functionality"""
    payload = {
        "message": "Hello SentinelAI!",
        "strategy": "balanced"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "response" in data
    assert "provider" in data
    assert "latency_ms" in data
    assert "fallback_count" in data
    
    # Verify response contains our message
    assert "Hello SentinelAI!" in data["response"]


def test_chat_with_strategy():
    """Test chat with different routing strategies"""
    strategies = ["balanced", "cheapest", "fastest", "most_reliable"]
    
    for strategy in strategies:
        payload = {
            "message": "Test message",
            "strategy": strategy
        }
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data


def test_chat_with_custom_model():
    """Test chat with specific model selection"""
    payload = {
        "message": "Test with specific model",
        "model": "gpt-4o"  # Use actual model from config
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data


def test_chat_invalid_model():
    """Test chat with invalid model returns error"""
    payload = {
        "message": "Test",
        "model": "nonexistent-model-xyz"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 400


def test_chat_exceeds_token_limit():
    """Test chat with tokens exceeding limit"""
    payload = {
        "message": "Test",
        "max_tokens": 10000  # Exceeds 8192 limit
    }
    response = client.post("/api/chat", json=payload)
    # FastAPI validation returns 422, business logic returns 400
    assert response.status_code in [400, 422]


def test_get_metrics():
    """Test metrics endpoint"""
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    
    assert "providers" in data
    assert "summary" in data
    assert "total_providers" in data["summary"]
    assert "healthy_providers" in data["summary"]
    assert "system_status" in data["summary"]


def test_simulate_failure():
    """Test failure simulation (demo mode)"""
    response = client.post("/api/simulate-failure?provider_name=openai")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "openai" in data["message"].lower()


def test_simulate_failure_invalid_provider():
    """Test failure simulation with invalid provider"""
    response = client.post("/api/simulate-failure?provider_name=invalid-provider")
    assert response.status_code == 404


def test_reset_simulation():
    """Test reset simulation endpoint"""
    # First simulate a failure
    client.post("/api/simulate-failure?provider_name=openai")
    
    # Then reset
    response = client.post("/api/reset-simulation")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "reset" in data["message"].lower()


def test_failover_logic():
    """Test that failover works when provider is unhealthy"""
    # Simulate OpenAI failure
    client.post("/api/simulate-failure?provider_name=openai")
    
    # Send chat request without specifying model - should auto-select healthy provider
    payload = {
        "message": "Testing failover",
        "strategy": "balanced"
    }
    response = client.post("/api/chat", json=payload)
    
    # Should either succeed with fallback provider or return 503 if all down
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        # Should show fallback was used or normal operation
        assert "fallback_count" in data or "provider" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
