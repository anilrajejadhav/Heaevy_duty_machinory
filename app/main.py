"""Application entry point for the TVH technical-case demo."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.routes import router
from app.recommendations.service import RecommendationService
from app.retrieval.search import CatalogSearch
from app.utils.config import PROJECT_ROOT, get_settings
from app.utils.logger import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare local storage and restore saved work when the server starts."""
    settings = get_settings()
    configure_logging(settings.log_level)
    settings.ensure_directories()
    app.state.settings = settings
    app.state.project_root = Path(PROJECT_ROOT)
    app.state.search = CatalogSearch()
    app.state.recommendations = RecommendationService()
    app.state.search.load(settings.index_path)
    app.state.recommendations.load(settings.recommendations_path)
    yield


app = FastAPI(
    title="TVH Findability Demo",
    description="Local product search and co-purchase recommendations for the AI case.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(router)
