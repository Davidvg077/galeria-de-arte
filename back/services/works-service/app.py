"""Compatibility entry point; the MVC implementation lives in works_service."""

import sys
from pathlib import Path

services_directory = str(Path(__file__).resolve().parents[1])
if services_directory not in sys.path:
    sys.path.insert(0, services_directory)

from works_service.main import app
from works_service.models import ArtistWorkInput
from works_service.models.repository import init_db

__all__ = ["app", "ArtistWorkInput", "init_db"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3002)
