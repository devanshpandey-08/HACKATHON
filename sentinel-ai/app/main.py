"""
SentinelAI - Main API Application
Production-ready AI orchestration with failover
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
import time
import logging
import os

from app.config import SentinelConfig, ProviderConfig
from app.health_monitor import HealthMonitor, ProviderHealth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SentinelAI",
    description="Self-Healing AI Orchestrator with Multi-Provider Failover",
    version="1.0.0"
)

# CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize config and health monitor
config = SentinelConfig.load_from_env()
health_monitor = HealthMonitor(config)

# Request/Response models
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    model: Optional[str] = Field(None, description="Preferred model (auto-selected if None)")
    temperature: float = Field(0.7, ge=0, le=2)
    max_tokens: int = Field(1024, ge=1, le=8192)
    strategy: str = Field("balanced", description="Routing strategy: balanced, cheapest, fastest, most_reliable")


class ChatResponse(BaseModel):
    response: str
    provider: str
    model: str
    latency_ms: float
    tokens_used: int
    cost_usd: float
    fallback_count: int = 0


class HealthStatus(BaseModel):
    provider: str
    healthy: bool
    latency_ms: float
    success_rate: float
    last_check: Optional[str]
    error_message: Optional[str]


# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting SentinelAI...")
    health_monitor.start()
    logger.info(f"Monitoring {len(config.providers)} providers: {list(config.providers.keys())}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    health_monitor.stop()
    logger.info("SentinelAI stopped")


@app.get("/")
async def root():
    return {
        "message": "Welcome to SentinelAI - The Self-Healing AI Orchestrator",
        "docs": "/docs",
        "health": "/health",
        "dashboard": "/dashboard"
    }


@app.get("/dashboard")
async def dashboard():
    """Serve the live dashboard"""
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"error": "Dashboard not found"}


@app.get("/health")
async def health_check():
    """Overall system health"""
    healthy_providers = health_monitor.get_healthy_providers()
    return {
        "status": "healthy" if healthy_providers else "degraded",
        "healthy_providers": healthy_providers,
        "total_providers": len(config.providers),
        "timestamp": time.time()
    }


@app.get("/api/providers", response_model=List[HealthStatus])
async def get_providers():
    """Get status of all AI providers"""
    all_health = health_monitor.get_all_health()
    return [
        HealthStatus(
            provider=name,
            healthy=h.is_healthy,
            latency_ms=round(h.latency_ms, 2),
            success_rate=round(h.success_rate, 2),
            last_check=h.last_check.isoformat() if h.last_check else None,
            error_message=h.error_message
        )
        for name, h in all_health.items()
    ]


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Send a chat message through SentinelAI orchestration layer.
    Automatically selects best provider and handles failover.
    """
    start_time = time.time()
    fallback_count = 0
    
    # Validate guardrails
    if request.max_tokens > config.max_tokens_limit:
        raise HTTPException(status_code=400, detail=f"max_tokens exceeds limit of {config.max_tokens_limit}")
    
    # Select provider based on strategy
    target_provider_name = None
    
    if request.model:
        # User specified model - find provider
        for prov_name, prov_config in config.providers.items():
            if request.model in prov_config.models:
                target_provider_name = prov_name
                break
        if not target_provider_name:
            raise HTTPException(status_code=400, detail=f"Model {request.model} not found")
    else:
        # Auto-select based on strategy
        if request.strategy == "cheapest":
            target_provider_name = health_monitor.get_best_provider('cost')
        elif request.strategy == "fastest":
            target_provider_name = health_monitor.get_best_provider('latency')
        elif request.strategy == "most_reliable":
            target_provider_name = health_monitor.get_best_provider('reliability')
        else:  # balanced
            target_provider_name = health_monitor.get_best_provider('balanced')
    
    if not target_provider_name:
        raise HTTPException(status_code=503, detail="No healthy providers available")
    
    # Try to send request with fallback logic
    attempted_providers = []
    max_retries = config.max_retries
    
    for attempt in range(max_retries):
        try:
            # Check if provider is healthy before calling
            provider_health = health_monitor.providers.get(target_provider_name)
            if provider_health and not provider_health.is_healthy:
                raise Exception(f"Provider {target_provider_name} is unhealthy")
            
            # Get provider config
            provider_config = config.providers.get(target_provider_name)
            if not provider_config:
                raise Exception(f"Provider {target_provider_name} configuration not found")
            
            # Simulate provider call (in production, this would call actual API)
            await asyncio.sleep(provider_config.avg_latency_ms / 1000 * 0.5)  # Simulated latency
            
            # Simulate successful response
            latency = (time.time() - start_time) * 1000
            
            # Mock response (in production, this comes from actual AI provider)
            mock_response = f"[SentinelAI via {target_provider_name}] I received your message: '{request.message}'. This is a production-ready demo showing the orchestration layer working correctly with automatic failover capabilities."
            
            # Calculate cost
            estimated_tokens = len(request.message.split()) * 2
            cost = (estimated_tokens / 1000) * provider_config.cost_per_1k_tokens
            
            return ChatResponse(
                response=mock_response,
                provider=target_provider_name,
                model=request.model or provider_config.models[0],
                latency_ms=round(latency, 2),
                tokens_used=estimated_tokens,
                cost_usd=round(cost, 6),
                fallback_count=fallback_count
            )
            
        except Exception as e:
            logger.warning(f"Provider {target_provider_name} failed: {str(e)}")
            attempted_providers.append(target_provider_name)
            fallback_count += 1
            
            # Find next healthy provider
            healthy = health_monitor.get_healthy_providers()
            next_provider = next((p for p in healthy if p not in attempted_providers), None)
            
            if not next_provider:
                raise HTTPException(
                    status_code=503,
                    detail=f"All providers failed. Attempted: {attempted_providers}"
                )
            
            target_provider_name = next_provider
            logger.info(f"Falling back to {target_provider_name}")
    
    # Should not reach here
    raise HTTPException(status_code=500, detail="Unexpected error in orchestration")


@app.get("/api/metrics")
async def get_metrics():
    """Get system metrics for dashboard"""
    all_health = health_monitor.get_all_health()
    
    avg_latency = sum(h.latency_ms for h in all_health.values()) / len(all_health) if all_health else 0
    healthy_count = sum(1 for h in all_health.values() if h.is_healthy)
    
    return {
        "providers": {
            name: {
                "healthy": h.is_healthy,
                "latency_ms": round(h.latency_ms, 2),
                "success_rate": round(h.success_rate, 2),
                "consecutive_failures": h.consecutive_failures
            }
            for name, h in all_health.items()
        },
        "summary": {
            "total_providers": len(all_health),
            "healthy_providers": healthy_count,
            "average_latency_ms": round(avg_latency, 2),
            "system_status": "healthy" if healthy_count > 0 else "down"
        }
    }


@app.post("/api/simulate-failure")
async def simulate_failure(provider_name: str):
    """
    DEMO ONLY: Simulate a provider failure for testing failover.
    This endpoint is for hackathon demonstration purposes.
    """
    if not config.demo_mode:
        raise HTTPException(status_code=403, detail="Demo mode disabled")
    
    if provider_name not in health_monitor.providers:
        raise HTTPException(status_code=404, detail=f"Provider {provider_name} not found")
    
    # Force provider to appear unhealthy
    health_monitor.providers[provider_name].is_healthy = False
    health_monitor.providers[provider_name].consecutive_failures = config.consecutive_failures_threshold
    health_monitor.providers[provider_name].error_message = "Simulated failure for demo"
    
    logger.info(f"Simulated failure for provider: {provider_name}")
    
    return {
        "message": f"Provider {provider_name} marked as unhealthy",
        "provider": provider_name,
        "status": "simulated_failure"
    }


@app.post("/api/reset-simulation")
async def reset_simulation():
    """Reset all simulated failures"""
    for health in health_monitor.providers.values():
        health.is_healthy = True
        health.consecutive_failures = 0
        health.error_message = None
    
    logger.info("Reset all simulated failures")
    
    return {"message": "All providers reset to healthy state"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)
