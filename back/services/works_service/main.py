from fastapi import FastAPI

from error_handling import install_exception_handlers

from .models.repository import init_db
from .views import router

app = FastAPI(title="Gart Gallery Works Service", version="1.0.0")
install_exception_handlers(app)
app.include_router(router)
app.add_event_handler("startup", init_db)
