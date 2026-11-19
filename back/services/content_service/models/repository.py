from psycopg.types.json import Json

from db import connection

from . import ArtistInput, ContentPageInput


def init_db() -> None:
    with connection() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS content_artists (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                biography TEXT NOT NULL DEFAULT '',
                image_url TEXT,
                active BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS content_pages (
                slug TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                published BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS content_landing (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                title TEXT NOT NULL,
                subtitle TEXT NOT NULL DEFAULT '',
                hero_image_url TEXT,
                featured_work_ids JSONB NOT NULL DEFAULT '[]'::jsonb
            )
            """
        )
        if db.execute("SELECT COUNT(*) AS count FROM content_artists").fetchone()["count"] == 0:
            with db.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO content_artists (id, name, biography, image_url, active)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [
                        (1, "Laura Méndez", "Pinta paisajes de memoria y territorio.", None, True),
                        (2, "Carlos Pérez", "Explora el color desde la abstracción.", None, True),
                        (3, "Ana Torres", "Crea composiciones llenas de luz.", None, True),
                        (4, "Miguel Ángel", "Retrata viajes, montañas y horizontes.", None, True),
                    ],
                )
            db.execute(
                "SELECT setval(pg_get_serial_sequence('content_artists', 'id'), "
                "COALESCE(MAX(id), 1), true) FROM content_artists"
            )
        if db.execute("SELECT COUNT(*) AS count FROM content_pages").fetchone()["count"] == 0:
            with db.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO content_pages (slug, title, body, published) VALUES (%s, %s, %s, TRUE)",
                    [
                        ("about", "Sobre GART Gallery", "Un espacio para descubrir arte, artistas y galerías."),
                        ("contact", "Contacto", "Escríbenos para conocer nuestras obras y exposiciones."),
                    ],
                )
        if db.execute("SELECT COUNT(*) AS count FROM content_landing").fetchone()["count"] == 0:
            db.execute(
                """
                INSERT INTO content_landing (id, title, subtitle, hero_image_url, featured_work_ids)
                VALUES (1, %s, %s, %s, %s)
                """,
                (
                    "Arte que inspira, espacios que conectan.",
                    "Descubre obras únicas de artistas increíbles en nuestras galerías.",
                    None,
                    Json([1, 2, 3, 4]),
                ),
            )


def get_content() -> tuple[dict, list[dict], list[dict]]:
    with connection() as db:
        landing = db.execute("SELECT * FROM content_landing WHERE id = 1").fetchone()
        pages = list(db.execute("SELECT * FROM content_pages ORDER BY slug"))
        artists = list(db.execute("SELECT * FROM content_artists ORDER BY id"))
    return landing, pages, artists


def get_landing() -> dict:
    with connection() as db:
        return db.execute("SELECT * FROM content_landing WHERE id = 1").fetchone()


def get_page(slug: str) -> dict | None:
    with connection() as db:
        return db.execute("SELECT * FROM content_pages WHERE slug = %s", (slug,)).fetchone()


def save_page(page: ContentPageInput) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT INTO content_pages (slug, title, body, published)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(slug) DO UPDATE SET
                title = excluded.title, body = excluded.body, published = excluded.published
            """,
            (page.slug, page.title, page.body, page.published),
        )


def get_artists() -> list[dict]:
    with connection() as db:
        return list(db.execute("SELECT * FROM content_artists ORDER BY id"))


def get_artist(artist_id: int) -> dict | None:
    with connection() as db:
        return db.execute("SELECT * FROM content_artists WHERE id = %s", (artist_id,)).fetchone()


def create_artist(artist: ArtistInput) -> dict:
    with connection() as db:
        return db.execute(
            """
            INSERT INTO content_artists (name, biography, image_url, active)
            VALUES (%s, %s, %s, %s) RETURNING *
            """,
            (artist.name, artist.biography, artist.image_url, artist.active),
        ).fetchone()


def update_artist(artist_id: int, artist: ArtistInput) -> dict | None:
    with connection() as db:
        return db.execute(
            """
            UPDATE content_artists SET name = %s, biography = %s, image_url = %s, active = %s
            WHERE id = %s RETURNING *
            """,
            (artist.name, artist.biography, artist.image_url, artist.active, artist_id),
        ).fetchone()
