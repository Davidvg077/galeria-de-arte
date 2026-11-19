import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "back" / "services"))

from content_service.main import app as content_app
from gallery_service.main import app as gallery_app


class MvcServiceRoutesTests(unittest.TestCase):
    def test_gallery_routes_are_registered(self):
        routes = gallery_app.openapi()["paths"]
        self.assertIn("/api/galleries", routes)
        self.assertIn("/api/galleries/{gallery_id}", routes)
        self.assertIn("/health", routes)

    def test_content_and_artist_routes_are_registered(self):
        routes = content_app.openapi()["paths"]
        self.assertIn("/api/content", routes)
        self.assertIn("/api/content/landing", routes)
        self.assertIn("/api/content/pages/{slug}", routes)
        self.assertIn("/api/artists", routes)
        self.assertIn("/api/artists/{artist_id}", routes)
        self.assertIn("/health", routes)


if __name__ == "__main__":
    unittest.main()
