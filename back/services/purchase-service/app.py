import sys
from pathlib import Path

from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from error_handling import install_exception_handlers
from purchase_service.models.repository import init_db
from purchase_service.controllers.routes import router


app = FastAPI(title="Gart Gallery Purchase Service", version="2.0.0")
install_exception_handlers(app)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "purchase", "status": "ok"}


app.include_router(router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3004)
