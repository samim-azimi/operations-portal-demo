import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KnowledgeBaseArticle, User
from app.security import get_current_user

router = APIRouter(prefix="/assistant", tags=["Portal Assistant"])


class AssistantQuestion(BaseModel):
    message: str = Field(min_length=2, max_length=1000)


QUICK_GUIDES = [
    ({"ticket", "issue", "support", "problem"}, "Create a Help Desk ticket with a clear subject, category, priority, description, and screenshot. You can follow every update under My Tickets.", "/submit"),
    ({"asset", "laptop", "equipment", "ims"}, "Open IMS to review assets assigned to you. Inventory officers can register and manage inventory items.", "/inventory/my-assets"),
    ({"stock", "mouse", "keyboard", "request"}, "Open Stock to browse available items and submit an internal material request. Quantity is reduced only after delivery.", "/stock"),
    ({"sign", "signature", "approve", "document"}, "Open Sign to review documents inside the portal. The portal records your identity, timestamp, verification number, and document hash.", "/sign"),
    ({"message", "chat", "call", "meeting"}, "Open LAN Messenger for internal chats, groups, attachments, meetings, and call sessions.", "/lan-messenger"),
]


@router.post("/query")
def assistant_query(
    data: AssistantQuestion,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    message = data.message.strip()
    tokens = {token for token in re.findall(r"[a-z0-9]+", message.lower()) if len(token) > 2}
    quick = next((item for item in QUICK_GUIDES if tokens & item[0]), None)
    articles = []
    if tokens:
        terms = [f"%{token}%" for token in list(tokens)[:8]]
        conditions = []
        for term in terms:
            conditions.extend([
                KnowledgeBaseArticle.title.ilike(term),
                KnowledgeBaseArticle.problem_description.ilike(term),
                KnowledgeBaseArticle.solution.ilike(term),
            ])
        candidates = db.query(KnowledgeBaseArticle).filter(or_(*conditions)).limit(12).all()
        scored = []
        for article in candidates:
            text = f"{article.title} {article.problem_description} {article.solution} {' '.join(article.tags or [])}".lower()
            score = sum(1 for token in tokens if token in text)
            if score:
                scored.append((score, article))
        articles = [article for _, article in sorted(scored, key=lambda item: item[0], reverse=True)[:3]]
    if articles:
        lead = articles[0]
        answer = f"{lead.title}: {lead.solution}"
    elif quick:
        answer = quick[1]
    else:
        answer = "I can guide you to Help Desk, IMS, Stock, Sign, LAN Messenger, or search approved knowledge articles. Tell me what you are trying to do."
    return {
        "answer": answer,
        "sources": [{"id": item.id, "title": item.title, "category": item.category} for item in articles],
        "action": {"label": "Open module", "route": quick[2]} if quick else None,
        "suggestions": ["Create a ticket", "Show my assets", "Request stock", "Sign a document"],
    }
