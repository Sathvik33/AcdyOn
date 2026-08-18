import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import routes
from app.core.config import settings

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="Acdyon Job Ingestion",
    description="Reliable ingestion of public job listings with resilience and visibility.",
    version="0.1.0",
)

app.include_router(routes.router)

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
INDEX_FILE = FRONTEND_DIST / "index.html"

if (FRONTEND_DIST / "assets").is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )


@app.get("/", include_in_schema=False)
def index():
    if not INDEX_FILE.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Frontend bundle not found. Run 'npm install && npm run build' in frontend/."
            },
        )
    return FileResponse(INDEX_FILE)
