from fastapi import APIRouter, Depends, Query

from app.schemas import Page, TaskRead
from app.security import require_permission

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
    dependencies=[Depends(require_permission("can_access_tasks"))],
)


@router.get("", response_model=Page[TaskRead])
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "pages": 0,
    }
