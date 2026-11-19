from fastapi import HTTPException

from ..models import (
    Artist,
    ArtistInput,
    ContentPage,
    ContentPageInput,
    LandingContent,
    artist_from_row,
    landing_from_row,
    page_from_row,
)
from ..models import repository


def get_content() -> dict[str, object]:
    landing, pages, artists = repository.get_content()
    return {
        "landing": landing_from_row(landing),
        "pages": [page_from_row(row) for row in pages],
        "artists": [artist_from_row(row) for row in artists],
    }


def get_landing() -> LandingContent:
    return landing_from_row(repository.get_landing())


def get_page(slug: str) -> ContentPage:
    row = repository.get_page(slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Content page not found")
    return page_from_row(row)


def save_page(payload: ContentPageInput) -> ContentPage:
    repository.save_page(payload)
    return ContentPage(**payload.model_dump())


def list_artists() -> list[Artist]:
    return [artist_from_row(row) for row in repository.get_artists()]


def get_artist(artist_id: int) -> Artist:
    row = repository.get_artist(artist_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Artist not found")
    return artist_from_row(row)


def create_artist(payload: ArtistInput) -> Artist:
    return artist_from_row(repository.create_artist(payload))


def update_artist(artist_id: int, payload: ArtistInput) -> Artist:
    row = repository.update_artist(artist_id, payload)
    if row is None:
        raise HTTPException(status_code=404, detail="Artist not found")
    return artist_from_row(row)
