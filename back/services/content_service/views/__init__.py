from fastapi import APIRouter, Depends

from auth_client import require_permission

from .. import controllers
from ..models import Artist, ArtistInput, ContentPage, ContentPageInput, LandingContent

router = APIRouter()


@router.get("/api/content")
def content() -> dict[str, object]:
    return controllers.get_content()


@router.get("/api/content/landing", response_model=LandingContent)
def get_landing() -> LandingContent:
    return controllers.get_landing()


@router.get("/api/content/pages/{slug}", response_model=ContentPage)
def get_page(slug: str) -> ContentPage:
    return controllers.get_page(slug)


@router.post("/api/content/pages", response_model=ContentPage, status_code=201)
def create_page(
    payload: ContentPageInput,
    _user: dict = Depends(require_permission("content:write")),
) -> ContentPage:
    return controllers.save_page(payload)


@router.get("/api/artists")
def list_artists() -> dict[str, list[Artist]]:
    return {"items": controllers.list_artists()}


@router.get("/api/artists/{artist_id}", response_model=Artist)
def get_artist(artist_id: int) -> Artist:
    return controllers.get_artist(artist_id)


@router.post("/api/artists", response_model=Artist, status_code=201)
def create_artist(
    payload: ArtistInput,
    _user: dict = Depends(require_permission("content:write")),
) -> Artist:
    return controllers.create_artist(payload)


@router.put("/api/artists/{artist_id}", response_model=Artist)
def update_artist(
    artist_id: int,
    payload: ArtistInput,
    _user: dict = Depends(require_permission("content:write")),
) -> Artist:
    return controllers.update_artist(artist_id, payload)
