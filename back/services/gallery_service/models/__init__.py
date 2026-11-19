from pydantic import BaseModel, Field


class Gallery(BaseModel):
    id: int
    name: str
    description: str = ""
    address: str = ""
    city: str = ""
    country: str = ""
    website: str | None = None
    phone: str = ""
    email: str = ""
    image_url: str | None = None
    additional_images: list[str] = Field(default_factory=list)
    artist_ids: list[int] = Field(default_factory=list)
    active: bool = True


class GalleryInput(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    address: str = ""
    city: str = ""
    country: str = ""
    website: str | None = None
    phone: str = ""
    email: str = ""
    image_url: str | None = None
    additional_images: list[str] = Field(default_factory=list)
    artist_ids: list[int] = Field(default_factory=list)
    active: bool = True


def gallery_from_row(row: dict) -> Gallery:
    return Gallery(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        address=row["address"],
        city=row["city"],
        country=row["country"],
        website=row["website"],
        phone=row["phone"],
        email=row["email"],
        image_url=row["image_url"],
        additional_images=row["additional_images"],
        artist_ids=row["artist_ids"],
        active=row["active"],
    )
