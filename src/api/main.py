from __future__ import annotations

from src.api._compat import CORSMiddleware, FastAPI
from src.api.routes.counter import router as counter_router
from src.api.routes.health import router as health_router
from src.api.routes.inspection import router as inspection_router
from src.api.routes.iot import router as iot_router
from src.api.routes.pages import router as pages_router
from src.api.routes.results import router as results_router
from src.api.routes.templates import router as template_router
from src.utils.paths import PROJECT_ROOT


def create_app() -> FastAPI:
    app = FastAPI(title="Garment Label Inspection API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve static files (CSS / JS / images)
    try:
        from fastapi.staticfiles import StaticFiles
        static_dir = PROJECT_ROOT / "src" / "ui" / "static"
        if static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    except Exception:  # pragma: no cover
        pass

    # API routes (prefixed /api/* to avoid collision with page routes)
    app.include_router(health_router)
    app.include_router(template_router, prefix="/api")
    app.include_router(inspection_router, prefix="/api")
    app.include_router(results_router, prefix="/api")
    app.include_router(counter_router, prefix="/api")
    app.include_router(iot_router, prefix="/api")

    # Web page routes (HTML, no prefix)
    app.include_router(pages_router)

    return app


app = create_app()
