import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Ticket,
    TicketVideoLink,
    User,
    UserRole,
    VideoArticle,
)
from app.schemas import VideoCreate, VideoRead
from app.security import get_current_user, require_permission, require_roles

router = APIRouter(prefix="/videos", tags=["Faza Help Desk Guidance"], dependencies=[Depends(require_permission("can_access_helpdesk"))])


@router.get("", response_model=list[VideoRead])
def list_videos(
    category: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(VideoArticle).filter(VideoArticle.is_active.is_(True))
    if category:
        query = query.filter(VideoArticle.category == category)
    return query.order_by(VideoArticle.updated_at.desc()).all()


@router.post("", response_model=VideoRead, status_code=201)
def create_video(
    data: VideoCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    item = VideoArticle(
        **data.model_dump(mode="json"), created_by_id=user.id
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{video_id}", response_model=VideoRead)
def update_video(
    video_id: int,
    data: VideoCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    item = db.get(VideoArticle, video_id)
    if not item:
        raise HTTPException(404, "Video not found")
    for field, value in data.model_dump(mode="json").items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{video_id}", status_code=204)
def remove_video(
    video_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    item = db.get(VideoArticle, video_id)
    if not item:
        raise HTTPException(404, "Video not found")
    item.is_active = False
    db.commit()


@router.get("/recommended/{ticket_id}", response_model=list[VideoRead])
def recommended_videos(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if user.role == UserRole.USER and ticket.requester_id != user.id:
        raise HTTPException(403, "You can only access your own tickets")
    manual_ids = [
        video_id
        for (video_id,) in db.query(TicketVideoLink.video_id)
        .filter(TicketVideoLink.ticket_id == ticket.id)
        .all()
    ]
    active = (
        db.query(VideoArticle)
        .filter(VideoArticle.is_active.is_(True))
        .all()
    )
    tokens = set(
        re.findall(
            r"[a-z0-9]+",
            f"{ticket.title} {ticket.description} {ticket.category} {ticket.requested_category or ''}".lower(),
        )
    )
    scored = []
    for video in active:
        haystack = set(
            re.findall(
                r"[a-z0-9]+",
                f"{video.title} {video.description} {video.category} {' '.join(video.tags or [])}".lower(),
            )
        )
        score = len(tokens & haystack)
        if video.category in {
            ticket.category,
            ticket.requested_category,
        }:
            score += 5
        if video.id in manual_ids:
            score += 100
        if score:
            scored.append((score, video))
    return [video for _, video in sorted(scored, key=lambda pair: pair[0], reverse=True)[:4]]


@router.post("/{video_id}/recommend/{ticket_id}", status_code=204)
def recommend_video_manually(
    video_id: int,
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT)),
):
    if not db.get(VideoArticle, video_id) or not db.get(Ticket, ticket_id):
        raise HTTPException(404, "Ticket or video not found")
    exists = (
        db.query(TicketVideoLink)
        .filter(
            TicketVideoLink.video_id == video_id,
            TicketVideoLink.ticket_id == ticket_id,
        )
        .first()
    )
    if not exists:
        db.add(
            TicketVideoLink(
                video_id=video_id,
                ticket_id=ticket_id,
                recommended_by_id=user.id,
            )
        )
        db.commit()
