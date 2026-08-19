import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import routes
from app.core.config import settings
from app.db.database import engine, Base
from app.db import models  # Ensures all SQLAlchemy models are registered

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def init_db():
    logger.info("Initializing database tables...")
    try:
        # Create missing tables (e.g. source_health, jobs, ingestion_runs)
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

    # Safely migrate existing tables if columns are missing
    try:
        with engine.connect() as conn:
            columns = [
                ("duration_seconds", "FLOAT"),
                ("parse_failures", "INTEGER DEFAULT 0"),
                ("duplicate_count", "INTEGER DEFAULT 0"),
                ("http_status", "INTEGER"),
                ("retry_count", "INTEGER DEFAULT 0"),
            ]
            for col_name, col_type in columns:
                try:
                    conn.execute(text(f"ALTER TABLE ingestion_runs ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                    conn.commit()
                except Exception as e:
                    logger.debug(f"Column migration check for {col_name}: {e}")
    except Exception as e:
        logger.debug(f"Database migration check skipped: {e}")


# Run DB initialization synchronously on module import
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Acdyon Job Ingestion",
    description="Reliable ingestion of public job listings with resilience and visibility.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(routes.router)

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
INDEX_FILE = FRONTEND_DIST / "index.html"

if FRONTEND_DIST.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets" if (FRONTEND_DIST / "assets").is_dir() else FRONTEND_DIST),
        name="assets",
    )


@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(request: Request, full_path: str = ""):
    # Do not intercept API or docs routes
    if full_path.startswith(("api/", "docs", "openapi.json", "health", "jobs", "ingestion", "stats", "sources")):
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    if INDEX_FILE.is_file():
        return FileResponse(INDEX_FILE)

    return JSONResponse(
        status_code=503,
        content={
            "detail": "Frontend bundle not found. Run 'npm install && npm run build' in frontend/."
        },
    )
