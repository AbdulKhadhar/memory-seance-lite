"""App factory and entry point.

Run:  python -m app.main
Dev:  uvicorn app.main:create_app --factory --reload
"""
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__, llm
from app.config import ROOT, Settings, load_settings
from app.database import Database
from app.routes import router

CSP = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Memory Séance Lite", version=__version__)
    app.state.settings = settings
    app.state.db = Database(settings.db_path)

    @app.exception_handler(llm.LLMError)
    async def llm_error_handler(_request: Request, exc: llm.LLMError):
        return JSONResponse(status_code=exc.status,
                            content={"detail": {"code": exc.code, "message": exc.message}})

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    app.include_router(router)
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index():
        return (ROOT / "templates" / "index.html").read_text(encoding="utf-8")

    return app


def main():
    settings = load_settings()
    print(f"Memory Séance Lite → http://{settings.host}:{settings.port}  (data: {settings.db_path})")
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
