"""Domain and request models for works."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Work(BaseModel):
    id: int
    title: str
    description: str = ""
    year: str = ""
    category: str = "Landscape Paintings"
    image_url: str | None = None
    artist_id: int | None = None
    artist_name: str | None = None
    gallery_id: int | None = None
    available: bool = True
    price: float | None = None
    moderation_status: str = "published"
    created_at: datetime


class WorkInput(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    year: str = ""
    category: str = "Landscape Paintings"
    image_url: str | None = None
    artist_id: int | None = None
    gallery_id: int | None = None
    available: bool = True
    price: float | None = Field(default=None, ge=0)
    moderation_status: str = "published"


class ArtistWorkInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    year: str = Field(default="", max_length=10)
    category: str = Field(default="Landscape Paintings", min_length=1, max_length=100)
    image_url: str | None = Field(default=None, max_length=2048)
    price: float | None = Field(default=None, ge=0)
    status: str = Field(default="draft", pattern="^(draft|published)$")


def work_from_row(row: dict) -> Work:
    created_at = row["created_at"]
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    return Work(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        year=row["year"],
        category=row["category"],
        image_url=row["image_url"],
        artist_id=row["artist_id"],
        artist_name=row["artist_name"],
        gallery_id=row["gallery_id"],
        available=row["available"],
        price=row["price"],
        moderation_status=row["moderation_status"],
        created_at=created_at,
    )


def update_values(payload: WorkInput) -> tuple[object, ...]:
    return (
        payload.title, payload.description, payload.year, payload.category,
        payload.image_url, payload.artist_id, payload.gallery_id, payload.available,
        payload.price, payload.moderation_status,
    )
