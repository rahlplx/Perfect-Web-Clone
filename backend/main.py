"""
Perfect Web Clone Backend
统一 FastAPI 入口

AI-powered web page extraction and cloning service.
Open-source version without authentication.

启动方式:
    python main.py
    或
    uvicorn main:app --reload --port 5100
"""

# Windows asyncio event loop policy fix for Python 3.8+ (especially 3.14+)
# This must be set before any other asyncio imports
# 修复 Windows 上 Python 3.8+ (尤其是 3.14+) 的 asyncio 事件循环策略问题
import sys
if sys.platform == 'win32':
    import asyncio
    # Use ProactorEventLoop for better subprocess support on Windows
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from infrastructure.di import get_container, Container

# Rate limiting with slowapi
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# ============================================
# Authentication (optional, enabled via API_KEY env var)
# ============================================
API_KEY = os.getenv("API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(request: Request, api_key: str = Depends(api_key_header)):
    """Verify API key if API_KEY is configured. Skip for health/docs."""
    if not API_KEY:
        return  # Auth disabled
    if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
        return  # Skip auth for health/docs
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Perfect Web Clone API",
    description="AI-powered web page extraction and cloning",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration - environment-based
# Set CORS_ORIGINS env var for production (comma-separated)
# Default: open for development, restricted for production
_cors_origins_str = os.getenv("CORS_ORIGINS", "")
_cors_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"

if _cors_origins_str:
    _cors_origins = [o.strip() for o in _cors_origins_str.split(",") if o.strip()]
else:
    # Open-source default: allow all origins (no credentials for safety)
    _cors_origins = ["*"]
    _cors_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Unified error response format
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"},
    )


# ============================================
# Register Routers
# ============================================

# Cache module (memory storage for extractions)
from cache import cache_router
app.include_router(cache_router)
logger.info("Registered: /api/cache/*")

# Extractor module (Playwright page extraction)
from extractor import extractor_router
app.include_router(extractor_router)
logger.info("Registered: /api/extractor/*")

# Agent module (WebSocket for clone agent)
from agent import agent_ws_router
app.include_router(agent_ws_router)
logger.info("Registered: /api/agent/*")

# Image proxy module (CORS proxy for images)
try:
    from image_proxy.routes import router as image_proxy_router
    app.include_router(image_proxy_router)
    logger.info("Registered: /api/image-proxy/*")
except ImportError as e:
    logger.warning(f"Image proxy module not available: {e}")

# Image downloader module (batch image download)
try:
    from image_downloader.routes_fastapi import router as image_downloader_router
    app.include_router(image_downloader_router)
    logger.info("Registered: /api/image-downloader/*")
except ImportError as e:
    logger.warning(f"Image downloader module not available: {e}")

# BoxLite module (backend sandbox environment)
try:
    from boxlite import boxlite_router, boxlite_ws_router
    from boxlite.routes import boxlite_agent_router
    app.include_router(boxlite_router)
    app.include_router(boxlite_ws_router)
    app.include_router(boxlite_agent_router)
    logger.info("Registered: /api/boxlite/*")
    logger.info("Registered: /api/boxlite/ws/*")
    logger.info("Registered: /api/boxlite-agent/*")
except ImportError as e:
    logger.warning(f"BoxLite module not available: {e}")

# Sources module (file-system based source storage)
try:
    from sources import sources_router
    app.include_router(sources_router)
    logger.info("Registered: /api/sources/*")
except ImportError as e:
    logger.warning(f"Sources module not available: {e}")

# Checkpoint module (project state checkpoints)
try:
    from checkpoint.routes import router as checkpoint_router
    app.include_router(checkpoint_router)
    logger.info("Registered: /api/checkpoints/*")
except ImportError as e:
    logger.warning(f"Checkpoint module not available: {e}")


# ============================================
# Root Endpoints
# ============================================

@app.get("/")
@limiter.limit("100/minute")
async def root(request: Request, _: None = Depends(verify_api_key)):
    """Root endpoint - API info"""
    return {
        "name": "Perfect Web Clone API",
        "version": "1.0.0",
        "description": "AI-powered web page extraction and cloning",
        "docs": "/docs",
        "endpoints": {
            "cache": "/api/cache",
            "extractor": "/api/extractor",
            "agent": "/api/agent",
            "boxlite": "/api/boxlite",
            "boxlite_agent": "/api/boxlite-agent",
            "sources": "/api/sources",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "perfect-web-clone",
        "version": "1.0.0",
    }


@app.get("/api/di")
async def di_health(container: Container = Depends(get_container)):
    """DI container health — shows which adapters are active."""
    return {
        "status": "healthy",
        "adapters": container.health(),
    }


# ============================================
# Project Naming API
# ============================================

class ProjectNameRequest(BaseModel):
    message: str


@app.post("/api/project-name")
@limiter.limit("30/minute")
async def generate_project_name(
    request: Request,
    project_request: ProjectNameRequest,
    _: None = Depends(verify_api_key),
    container: Container = Depends(get_container),
):
    """Generate a short project name using async LLM adapter."""
    try:
        from ports.llm import LLMMessage

        llm = container.llm_provider
        messages = [LLMMessage(role="user", content=f"Generate a short project name (2-5 words) for: {project_request.message}")]
        response = await llm.complete(messages, model="claude-3-5-haiku-latest", max_tokens=50)
        name = response.content.strip().strip('"\'')
        logger.info(f"Generated project name: {name}")
        return {"name": name}

    except Exception as e:
        logger.error(f"Error generating project name: {e}")
        return {"name": "Untitled Project"}


# ============================================
# Startup/Shutdown Events
# ============================================

async def kill_port(port: int) -> bool:
    """Kill any process using the specified port"""
    import subprocess
    try:
        # Find process using the port
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True
        )
        pids = result.stdout.strip().split('\n')

        killed = False
        for pid in pids:
            if pid.strip():
                try:
                    subprocess.run(["kill", "-9", pid.strip()], check=True)
                    logger.info(f"Killed process {pid} on port {port}")
                    killed = True
                except Exception as e:
                    logger.warning(f"Failed to kill process {pid}: {e}")

        return killed
    except Exception as e:
        logger.warning(f"Error checking port {port}: {e}")
        return False


@app.on_event("startup")
async def startup_event():
    """Run on startup"""
    logger.info("=" * 50)
    logger.info("Perfect Web Clone API Starting...")
    logger.info("=" * 50)

    # Initialize DI container
    container = get_container()
    app.state.container = container
    logger.info(f"DI container initialized: {container.health()}")

    # Clean up BoxLite dev server port (8080) on startup
    dev_port = int(os.getenv("BOXLITE_DEV_PORT", "8080"))
    logger.info(f"Cleaning up port {dev_port} for BoxLite dev server...")
    await kill_port(dev_port)

    # Check required environment variables (support both direct and proxy API)
    has_api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_PROXY_API_KEY")
    if not has_api_key:
        logger.warning("No API key set (ANTHROPIC_API_KEY or CLAUDE_PROXY_API_KEY) - Agent features will not work!")
    else:
        if os.getenv("CLAUDE_PROXY_API_KEY"):
            logger.info("Using Claude proxy API")

    port_for_log = os.getenv("PORT", "5100")
    logger.info(f"API documentation available at: http://localhost:{port_for_log}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on shutdown"""
    logger.info("Perfect Web Clone API Shutting down...")

    # Cleanup Playwright browser
    try:
        from extractor import playwright_extractor_service
        await playwright_extractor_service.close()
        logger.info("Playwright browser closed")
    except Exception as e:
        logger.warning(f"Error closing Playwright: {e}")


# ============================================
# Main Entry Point
# ============================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "5100"))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )
