"""HTTP routes that expose works use cases."""

from fastapi import APIRouter, Depends, Query, status

from auth_client import require_permission

from .. import controllers
from ..models import ArtistWorkInput, Work, WorkInput

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"service": "works", "status": "ok"}


@router.get("/api/works")
def list_works(
    q: str = Query(default=""),
    category: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=6, ge=1, le=50),
) -> dict[str, object]:
    return controllers.list_works(q=q, category=category, page=page, limit=limit)


@router.get("/api/works/mine")
def list_my_works(
    user: dict = Depends(require_permission("works:submit")),
) -> dict[str, list[Work]]:
    return controllers.list_my_works(user)


@router.post(
    "/api/works/submissions",
    response_model=Work,
    status_code=status.HTTP_201_CREATED,
)
def create_artist_work(
    payload: ArtistWorkInput,
    user: dict = Depends(require_permission("works:submit")),
) -> Work:
    return controllers.create_artist_work(payload, user)


@router.get("/api/works/{work_id}", response_model=Work)
def get_work(work_id: int) -> Work:
    return controllers.get_work(work_id)


@router.put("/api/works/{work_id}/submission", response_model=Work)
def update_artist_work(
    work_id: int,
    payload: ArtistWorkInput,
    user: dict = Depends(require_permission("works:submit")),
) -> Work:
    return controllers.update_artist_work(work_id, payload, user)


@router.delete("/api/works/{work_id}/submission")
def delete_artist_work(
    work_id: int,
    user: dict = Depends(require_permission("works:submit")),
) -> dict[str, bool]:
    return controllers.delete_artist_work(work_id, user)


@router.post(
    "/api/works",
    response_model=Work,
    status_code=status.HTTP_201_CREATED,
)
def create_work(
    payload: WorkInput,
    _user: dict = Depends(require_permission("works:write")),
) -> Work:
    return controllers.create_work(payload)


@router.put("/api/works/{work_id}", response_model=Work)
def update_work(
    work_id: int,
    payload: WorkInput,
    _user: dict = Depends(require_permission("works:write")),
) -> Work:
    return controllers.update_work(work_id, payload)


@router.delete("/api/works/{work_id}")
def delete_work(
    work_id: int,
    _user: dict = Depends(require_permission("works:write")),
) -> dict[str, bool]:
    return controllers.delete_work(work_id)


@router.patch("/api/works/{work_id}/moderation", response_model=Work)
def moderate_work(
    work_id: int,
    moderation_status: str = Query(..., pattern="^(draft|pending|published|rejected)$"),
    _user: dict = Depends(require_permission("works:write")),
) -> Work:
    return controllers.moderate_work(work_id, moderation_status)
