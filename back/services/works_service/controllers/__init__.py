"""Use-case and business logic for works API operations."""

from fastapi import HTTPException

from datetime import datetime, timezone

from ..models import ArtistWorkInput, Work, WorkInput, repository, work_from_row


def list_works(
    q: str = "", category: str = "", page: int = 1, limit: int = 6,
) -> dict[str, object]:
    works = [work_from_row(row) for row in repository.list_published()]
    query = q.strip().lower()
    filtered = [
        work for work in works
        if (not query or query in f"{work.title} {work.description} {work.year}".lower())
        and (not category.strip() or work.category == category.strip())
    ]
    filtered.sort(key=lambda work: work.created_at, reverse=True)
    total = len(filtered)
    start = (page - 1) * limit
    return {
        "items": filtered[start:start + limit],
        "pagination": {
            "page": page,
            "limit": limit,
            "totalItems": total,
            "totalPages": max(1, (total + limit - 1) // limit),
        },
    }


def list_my_works(user: dict) -> dict[str, list[Work]]:
    rows = repository.list_owned(user["id"])
    return {"items": [work_from_row(row) for row in rows]}


def create_artist_work(payload: ArtistWorkInput, user: dict) -> Work:
    created_at = datetime.now(timezone.utc)
    available = payload.status == "published"
    work_id = repository.create_artist_work(payload, user, created_at)
    return Work(
        id=work_id, title=payload.title, description=payload.description,
        year=payload.year, category=payload.category, image_url=payload.image_url,
        artist_name=user["username"], available=available, price=payload.price,
        moderation_status=payload.status, created_at=created_at,
    )


def get_work(work_id: int) -> Work:
    row = repository.get_published(work_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Work not found")
    return work_from_row(row)


def update_artist_work(work_id: int, payload: ArtistWorkInput, user: dict) -> Work:
    created_at = repository.update_artist_work(work_id, user["id"], payload)
    if created_at is None:
        raise HTTPException(status_code=404, detail="Work not found")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    available = payload.status == "published"
    return Work(
        id=work_id, title=payload.title, description=payload.description,
        year=payload.year, category=payload.category, image_url=payload.image_url,
        artist_name=user["username"], available=available, price=payload.price,
        moderation_status=payload.status, created_at=created_at,
    )


def delete_artist_work(work_id: int, user: dict) -> dict[str, bool]:
    if not repository.delete_artist_work(work_id, user["id"]):
        raise HTTPException(status_code=404, detail="Work not found")
    return {"ok": True}


def create_work(payload: WorkInput) -> Work:
    created_at = datetime.now(timezone.utc)
    work_id = repository.create_work(payload, created_at)
    return Work(id=work_id, created_at=created_at, **payload.model_dump())


def update_work(work_id: int, payload: WorkInput) -> Work:
    created_at = repository.update_work(work_id, payload)
    if created_at is None:
        raise HTTPException(status_code=404, detail="Work not found")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    return Work(id=work_id, created_at=created_at, **payload.model_dump())


def delete_work(work_id: int) -> dict[str, bool]:
    if not repository.delete_work(work_id):
        raise HTTPException(status_code=404, detail="Work not found")
    return {"ok": True}


def moderate_work(work_id: int, moderation_status: str) -> Work:
    row = repository.moderate_work(work_id, moderation_status)
    if row is None:
        raise HTTPException(status_code=404, detail="Work not found")
    return work_from_row(row)
