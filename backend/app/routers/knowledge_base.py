from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KnowledgeBaseArticle, UserRole
from app.pagination import page_result
from app.schemas import KbCreate, KbRead, Page
from app.security import get_current_user, require_permission, require_roles
from app.services.knowledge_search import index_article

router = APIRouter(
    prefix="/knowledge-base",
    tags=["Knowledge"],
    dependencies=[Depends(require_permission("can_access_knowledge"))],
)


@router.get("", response_model=Page[KbRead])
def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=200),
    category: str | None = Query(None, max_length=80),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    query = db.query(KnowledgeBaseArticle)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                KnowledgeBaseArticle.title.ilike(term),
                KnowledgeBaseArticle.problem_description.ilike(term),
                KnowledgeBaseArticle.solution.ilike(term),
            )
        )
    if category and category != "All":
        query = query.filter(KnowledgeBaseArticle.category == category)
    return page_result(
        query.order_by(KnowledgeBaseArticle.updated_at.desc()), page, page_size
    )


@router.post("", response_model=KbRead, status_code=201)
def create_article(
    data: KbCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles(UserRole.ADMIN)),
):
    article = KnowledgeBaseArticle(
        **data.model_dump(), created_by_id=user.id
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    index_article(article)
    return article


@router.put("/{article_id}", response_model=KbRead)
def update_article(
    article_id: int,
    data: KbCreate,
    db: Session = Depends(get_db),
    _=Depends(require_roles(UserRole.ADMIN)),
):
    article = db.get(KnowledgeBaseArticle, article_id)
    if not article:
        raise HTTPException(404, "Article not found")
    for field, value in data.model_dump().items():
        setattr(article, field, value)
    db.commit()
    db.refresh(article)
    index_article(article)
    return article


@router.delete("/{article_id}", status_code=204)
def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles(UserRole.ADMIN)),
):
    article = db.get(KnowledgeBaseArticle, article_id)
    if not article:
        raise HTTPException(404, "Article not found")
    db.delete(article)
    db.commit()
