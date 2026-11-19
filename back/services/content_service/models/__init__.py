from pydantic import BaseModel, Field


class Artist(BaseModel):
    id: int
    name: str
    biography: str = ""
    image_url: str | None = None
    active: bool = True


class ArtistInput(BaseModel):
    name: str = Field(min_length=1)
    biography: str = ""
    image_url: str | None = None
    active: bool = True


class ContentPage(BaseModel):
    slug: str
    title: str
    body: str
    published: bool = True


class LandingContent(BaseModel):
    title: str
    subtitle: str = ""
    hero_image_url: str | None = None
    featured_work_ids: list[int] = Field(default_factory=list)


class ContentPageInput(BaseModel):
    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str
    published: bool = True


def artist_from_row(row: dict) -> Artist:
    return Artist(
        id=row["id"],
        name=row["name"],
        biography=row["biography"],
        image_url=row["image_url"],
        active=row["active"],
    )


def page_from_row(row: dict) -> ContentPage:
    return ContentPage(
        slug=row["slug"],
        title=row["title"],
        body=row["body"],
        published=row["published"],
    )


def landing_from_row(row: dict) -> LandingContent:
    return LandingContent(
        title=row["title"],
        subtitle=row["subtitle"],
        hero_image_url=row["hero_image_url"],
        featured_work_ids=row["featured_work_ids"],
    )
