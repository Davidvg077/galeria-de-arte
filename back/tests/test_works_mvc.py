import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "back" / "services"))

from works_service.controllers import list_works
from works_service.main import app
from works_service.models import Work


class WorksMvcTests(unittest.TestCase):
    def test_api_routes_are_registered(self):
        routes = {
            (method, route.path)
            for route in app.routes
            for method in getattr(route, "methods", set())
        }
        expected = {
            ("GET", "/health"),
            ("GET", "/api/works"),
            ("GET", "/api/works/mine"),
            ("POST", "/api/works/submissions"),
            ("GET", "/api/works/{work_id}"),
            ("PUT", "/api/works/{work_id}/submission"),
            ("DELETE", "/api/works/{work_id}/submission"),
            ("POST", "/api/works"),
            ("PUT", "/api/works/{work_id}"),
            ("DELETE", "/api/works/{work_id}"),
            ("PATCH", "/api/works/{work_id}/moderation"),
        }
        self.assertTrue(expected.issubset(routes))

    def test_controller_preserves_filtering_and_pagination(self):
        works = [
            Work(
                id=1,
                title="Paisaje azul",
                description="",
                year="2025",
                category="Landscape Paintings",
                created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            ).model_dump(),
            Work(
                id=2,
                title="Estudio rojo",
                description="",
                year="2024",
                category="Abstract",
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            ).model_dump(),
        ]
        with patch("works_service.controllers.repository.list_published", return_value=works):
            result = list_works(q="azul", page=1, limit=1)
        self.assertEqual([work.id for work in result["items"]], [1])
        self.assertEqual(result["pagination"]["totalItems"], 1)


if __name__ == "__main__":
    unittest.main()
