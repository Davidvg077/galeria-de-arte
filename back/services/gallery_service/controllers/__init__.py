from fastapi import HTTPException

from ..models import Gallery, GalleryInput, gallery_from_row
from ..models import repository


def list_galleries() -> list[Gallery]:
    return [gallery_from_row(row) for row in repository.get_all()]


def get_gallery(gallery_id: int) -> Gallery:
    row = repository.get_by_id(gallery_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Gallery not found")
    return gallery_from_row(row)


def create_gallery(payload: GalleryInput) -> Gallery:
    return gallery_from_row(repository.create(payload))


def update_gallery(gallery_id: int, payload: GalleryInput) -> Gallery:
    row = repository.update(gallery_id, payload)
    if row is None:
        raise HTTPException(status_code=404, detail="Gallery not found")
    return gallery_from_row(row)
