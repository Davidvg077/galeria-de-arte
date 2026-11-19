from fastapi import APIRouter, Depends

from auth_client import require_permission

from .. import controllers
from ..models import Gallery, GalleryInput

router = APIRouter()


@router.get("/api/galleries")
def list_galleries() -> dict[str, list[Gallery]]:
    return {"items": controllers.list_galleries()}


@router.get("/api/galleries/{gallery_id}", response_model=Gallery)
def get_gallery(gallery_id: int) -> Gallery:
    return controllers.get_gallery(gallery_id)


@router.post("/api/galleries", response_model=Gallery, status_code=201)
def create_gallery(
    payload: GalleryInput,
    _user: dict = Depends(require_permission("galleries:write")),
) -> Gallery:
    return controllers.create_gallery(payload)


@router.put("/api/galleries/{gallery_id}", response_model=Gallery)
def update_gallery(
    gallery_id: int,
    payload: GalleryInput,
    _user: dict = Depends(require_permission("galleries:write")),
) -> Gallery:
    return controllers.update_gallery(gallery_id, payload)
