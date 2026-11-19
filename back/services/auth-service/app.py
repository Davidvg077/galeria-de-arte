import sys
from pathlib import Path

from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from error_handling import install_exception_handlers
from auth_service.models.repository import init_db
from auth_service.controllers.routes import router


app = FastAPI(title="Gart Gallery Auth Service", version="2.0.0")
install_exception_handlers(app)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "auth", "status": "ok"}


app.include_router(router, prefix="/api/auth")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3003)
