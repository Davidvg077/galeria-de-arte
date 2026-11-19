import logging

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


logger = logging.getLogger("gart.services")


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(psycopg.OperationalError)
    async def database_unavailable(_request: Request, error: psycopg.OperationalError) -> JSONResponse:
        logger.error(
            "Database is unavailable.",
            exc_info=(type(error), error, error.__traceback__),
        )
        return JSONResponse(status_code=503, content={"detail": "Service is temporarily unavailable."})

    @app.exception_handler(psycopg.Error)
    async def database_error(_request: Request, error: psycopg.Error) -> JSONResponse:
        logger.error(
            "Database operation failed.",
            exc_info=(type(error), error, error.__traceback__),
        )
        return JSONResponse(status_code=500, content={"detail": "The request could not be completed."})

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, error: Exception) -> JSONResponse:
        logger.error(
            "Unexpected service error.",
            exc_info=(type(error), error, error.__traceback__),
        )
        return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})
