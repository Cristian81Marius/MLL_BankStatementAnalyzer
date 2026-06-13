from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Bank Statement Analyzer",
        description="Extracts and categorizes transactions from bank statement PDFs using AI.",
        version="1.0.0",
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")
    return app


app = create_app()
