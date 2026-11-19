"""Persistence operations for the works domain."""

from db import connection

from datetime import datetime, timezone

from . import ArtistWorkInput, Work, WorkInput, update_values


def init_db() -> None:
    with connection() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS works_works (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                year TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'Landscape Paintings',
                image_url TEXT,
                artist_id INTEGER,
                gallery_id INTEGER,
                available BOOLEAN NOT NULL DEFAULT TRUE,
                price REAL,
                moderation_status TEXT NOT NULL DEFAULT 'published',
                created_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        db.execute("ALTER TABLE works_works ADD COLUMN IF NOT EXISTS owner_user_id INTEGER")
        db.execute("ALTER TABLE works_works ADD COLUMN IF NOT EXISTS artist_name TEXT")
        if db.execute("SELECT COUNT(*) AS count FROM works_works").fetchone()["count"] == 0:
            seed = [
                Work(
                    id=1, title="Reflejos del alma", description="Una exploración de luz y memoria.",
                    year="2024", category="Landscape Paintings",
                    image_url="https://images.unsplash.com/photo-1549490349-8643362247b5?auto=format&fit=crop&w=700&q=85",
                    artist_id=1, gallery_id=1, available=True, price=1200000,
                    created_at=datetime(2024, 5, 1, tzinfo=timezone.utc),
                ),
                Work(
                    id=2, title="Naturaleza abstracta", description="Texturas y color en movimiento.",
                    year="2025", category="Abstract Oil Paintings",
                    image_url="https://images.unsplash.com/photo-1577083288073-40892c0860a4?auto=format&fit=crop&w=700&q=85",
                    artist_id=2, gallery_id=2, available=True, price=950000,
                    created_at=datetime(2024, 5, 2, tzinfo=timezone.utc),
                ),
                Work(
                    id=3, title="Sueños de colores", description="Una composición sobre libertad e imaginación.",
                    year="2024", category="Abstract Watercolours",
                    image_url="https://images.unsplash.com/photo-1579783902614-a3fb3927b6a5?auto=format&fit=crop&w=700&q=85",
                    artist_id=3, gallery_id=1, available=True, price=1500000,
                    created_at=datetime(2024, 5, 3, tzinfo=timezone.utc),
                ),
                Work(
                    id=4, title="Travesía", description="Paisaje de viaje y contemplación.",
                    year="2023", category="Landscape Paintings",
                    image_url="https://images.unsplash.com/photo-1561214115-f2f134cc4912?auto=format&fit=crop&w=700&q=85",
                    artist_id=4, gallery_id=3, available=False, price=800000,
                    created_at=datetime(2024, 5, 4, tzinfo=timezone.utc),
                ),
            ]
            with db.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO works_works (
                        id, title, description, year, category, image_url, artist_id,
                        gallery_id, available, price, moderation_status, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            work.id, work.title, work.description, work.year, work.category,
                            work.image_url, work.artist_id, work.gallery_id, work.available,
                            work.price, work.moderation_status, work.created_at.isoformat(),
                        )
                        for work in seed
                    ],
                )
            db.execute(
                "SELECT setval(pg_get_serial_sequence('works_works', 'id'), "
                "COALESCE(MAX(id), 1), true) FROM works_works"
            )


def list_published() -> list[dict]:
    with connection() as db:
        return db.execute(
            "SELECT * FROM works_works WHERE moderation_status = 'published'"
        ).fetchall()


def list_owned(owner_id: int) -> list[dict]:
    with connection() as db:
        return db.execute(
            "SELECT * FROM works_works WHERE owner_user_id = %s ORDER BY created_at DESC",
            (owner_id,),
        ).fetchall()


def create_artist_work(payload: ArtistWorkInput, user: dict, created_at: datetime) -> int:
    available = payload.status == "published"
    with connection() as db:
        cursor = db.execute(
            """
            INSERT INTO works_works (
                title, description, year, category, image_url, available, price,
                moderation_status, created_at, owner_user_id, artist_name
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                payload.title, payload.description, payload.year, payload.category,
                payload.image_url, available, payload.price, payload.status,
                created_at, user["id"], user["username"],
            ),
        )
        return cursor.fetchone()["id"]


def get_published(work_id: int) -> dict | None:
    with connection() as db:
        return db.execute(
            "SELECT * FROM works_works WHERE id = %s AND moderation_status = 'published'",
            (work_id,),
        ).fetchone()


def update_artist_work(
    work_id: int, owner_id: int, payload: ArtistWorkInput,
) -> datetime | None:
    available = payload.status == "published"
    with connection() as db:
        row = db.execute(
            "SELECT created_at FROM works_works WHERE id = %s AND owner_user_id = %s",
            (work_id, owner_id),
        ).fetchone()
        if row is None:
            return None
        db.execute(
            """
            UPDATE works_works SET title = %s, description = %s, year = %s,
                category = %s, image_url = %s, price = %s,
                moderation_status = %s, available = %s
            WHERE id = %s AND owner_user_id = %s
            """,
            (
                payload.title, payload.description, payload.year, payload.category,
                payload.image_url, payload.price, payload.status, available,
                work_id, owner_id,
            ),
        )
        return row["created_at"]


def delete_artist_work(work_id: int, owner_id: int) -> bool:
    with connection() as db:
        cursor = db.execute(
            "DELETE FROM works_works WHERE id = %s AND owner_user_id = %s",
            (work_id, owner_id),
        )
        return cursor.rowcount > 0


def create_work(payload: WorkInput, created_at: datetime) -> int:
    with connection() as db:
        cursor = db.execute(
            """
            INSERT INTO works_works (
                title, description, year, category, image_url, artist_id, gallery_id,
                available, price, moderation_status, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (*update_values(payload), created_at.isoformat()),
        )
        return cursor.fetchone()["id"]


def update_work(work_id: int, payload: WorkInput) -> datetime | None:
    with connection() as db:
        row = db.execute(
            "SELECT created_at FROM works_works WHERE id = %s", (work_id,),
        ).fetchone()
        if row is None:
            return None
        db.execute(
            """
            UPDATE works_works SET title = %s, description = %s, year = %s, category = %s,
                image_url = %s, artist_id = %s, gallery_id = %s, available = %s,
                price = %s, moderation_status = %s
            WHERE id = %s
            """,
            (*update_values(payload), work_id),
        )
        return row["created_at"]


def delete_work(work_id: int) -> bool:
    with connection() as db:
        cursor = db.execute("DELETE FROM works_works WHERE id = %s", (work_id,))
        return cursor.rowcount > 0


def moderate_work(work_id: int, moderation_status: str) -> dict | None:
    with connection() as db:
        row = db.execute(
            "SELECT * FROM works_works WHERE id = %s", (work_id,),
        ).fetchone()
        if row is None:
            return None
        db.execute(
            "UPDATE works_works SET moderation_status = %s WHERE id = %s",
            (moderation_status, work_id),
        )
        return db.execute(
            "SELECT * FROM works_works WHERE id = %s", (work_id,),
        ).fetchone()
