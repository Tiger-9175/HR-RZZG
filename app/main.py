"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, load_config_from_file
from app.core.db import init_db
from app.api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Load persisted LLM config (overrides env defaults if exists)
    loaded = load_config_from_file()

    # Re-init LLM client with persisted config
    from app.core.llm import llm_client
    llm_client._init_client()
    if loaded:
        llm_client.mark_configured()

    # Load qualification standards
    from app.evaluation.engine import init_standards
    init_standards(settings.demo_dir)

    # Ensure directories / database exist
    Path(settings.upload_dir).mkdir(exist_ok=True)
    Path(settings.data_dir).mkdir(exist_ok=True)
    init_db()

    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"LLM configured: {llm_client.is_configured}, endpoint: {settings.llm_base_url}")

    yield

    logger.info("Application shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router)

# Serve static frontend files (in production)
static_dir = Path("frontend/dist")
if static_dir.exists():
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """Serve built files, falling back to index.html for SPA routes."""
        if full_path.startswith("api/"):
            raise HTTPException(404, "接口不存在")
        target = (static_dir / full_path).resolve()
        if full_path and target.is_file():
            return FileResponse(target)
        # A missing static resource (e.g. favicon.svg) should 404, not HTML
        if "." in Path(full_path).name:
            raise HTTPException(404, "资源不存在")
        return FileResponse(static_dir / "index.html")

    logger.info(f"Serving frontend from {static_dir}")
else:
    logger.warning("Frontend dist not found, API only mode")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
