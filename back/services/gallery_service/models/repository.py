from psycopg.types.json import Json

from db import connection

from . import Gallery, GalleryInput


def init_db() -> None:
    with connection() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS gallery_galleries (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                address TEXT NOT NULL DEFAULT '',
                city TEXT NOT NULL DEFAULT '',
                country TEXT NOT NULL DEFAULT '',
                website TEXT,
                phone TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                image_url TEXT,
                additional_images JSONB NOT NULL DEFAULT '[]'::jsonb,
                artist_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                active BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )
        if db.execute("SELECT COUNT(*) AS count FROM gallery_galleries").fetchone()["count"] == 0:
            seed = [
                Gallery(
                    id=1, name="GART Gallery", description="Arte contemporáneo colombiano.",
                    address="Carrera 7 # 72-41", city="Bogotá", country="Colombia",
                    phone="+57 601 555 0101", email="hola@gartgallery.co",
                    website="https://gartgallery.co", artist_ids=[1, 3],
                    image_url="https://images.unsplash.com/photo-1561214115-f2f134cc4912?auto=format&fit=crop&w=1200&q=85",
                ),
                Gallery(
                    id=2, name="Galería Horizonte", description="Nuevas miradas y territorios.",
                    address="Carrera 37 # 10-28", city="Medellín", country="Colombia",
                    phone="+57 604 555 0102", email="contacto@horizonte.co", artist_ids=[2],
                    image_url="https://images.unsplash.com/photo-1577083552431-6e5fd01aa342?auto=format&fit=crop&w=1200&q=85",
                ),
                Gallery(
                    id=3, name="Arte Vivo", description="Espacio para artistas emergentes.",
                    address="Calle 5 # 4-18", city="Cali", country="Colombia",
                    phone="+57 602 555 0103", email="hola@artevivo.co", artist_ids=[4],
                    image_url="https://images.unsplash.com/photo-1577083288073-40892c0860a4?auto=format&fit=crop&w=1200&q=85",
                ),
                Gallery(
                    id=4, name="Espacio Creativo", description="Exposiciones y encuentros.",
                    address="Carrera 53 # 76-12", city="Barranquilla", country="Colombia",
                    phone="+57 605 555 0104", email="info@espaciocreativo.co", artist_ids=[],
                    image_url="https://images.unsplash.com/photo-1594784051650-5a5e8e8a0c6f?auto=format&fit=crop&w=1200&q=85",
                ),
            ]
            with db.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO gallery_galleries (
                        id, name, description, address, city, country, website, phone,
                        email, image_url, additional_images, artist_ids, active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            gallery.id, gallery.name, gallery.description, gallery.address,
                            gallery.city, gallery.country, gallery.website, gallery.phone,
                            gallery.email, gallery.image_url, Json(gallery.additional_images),
                            Json(gallery.artist_ids), gallery.active,
                        )
                        for gallery in seed
                    ],
                )
            db.execute(
                "SELECT setval(pg_get_serial_sequence('gallery_galleries', 'id'), "
                "COALESCE(MAX(id), 1), true) FROM gallery_galleries"
            )


def get_all() -> list[dict]:
    with connection() as db:
        return list(db.execute("SELECT * FROM gallery_galleries ORDER BY id"))


def get_by_id(gallery_id: int) -> dict | None:
    with connection() as db:
        return db.execute("SELECT * FROM gallery_galleries WHERE id = %s", (gallery_id,)).fetchone()


def create(payload: GalleryInput) -> dict:
    with connection() as db:
        return db.execute(
            """
            INSERT INTO gallery_galleries (
                name, description, address, city, country, website, phone, email,
                image_url, additional_images, artist_ids, active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                payload.name, payload.description, payload.address, payload.city,
                payload.country, payload.website, payload.phone, payload.email,
                payload.image_url, Json(payload.additional_images),
                Json(payload.artist_ids), payload.active,
            ),
        ).fetchone()


def update(gallery_id: int, payload: GalleryInput) -> dict | None:
    with connection() as db:
        return db.execute(
            """
            UPDATE gallery_galleries SET name = %s, description = %s, address = %s, city = %s,
                country = %s, website = %s, phone = %s, email = %s, image_url = %s,
                additional_images = %s, artist_ids = %s, active = %s
            WHERE id = %s
            RETURNING *
            """,
            (
                payload.name, payload.description, payload.address, payload.city,
                payload.country, payload.website, payload.phone, payload.email,
                payload.image_url, Json(payload.additional_images),
                Json(payload.artist_ids), payload.active, gallery_id,
            ),
        ).fetchone()
