from fastapi import FastAPI

from error_handling import install_exception_handlers

from .models.repository import init_db
from .views import router

app = FastAPI(title="Gart Gallery Content Service", version="1.0.0")
install_exception_handlers(app)
app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "content", "status": "ok"}
