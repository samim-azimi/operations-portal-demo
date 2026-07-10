import enum
from datetime import datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

def utcnow(): return datetime.now(timezone.utc)
class UserRole(str, enum.Enum):
    SUPER_ADMIN="super_admin"
    ADMIN="admin"
    SUPPORT="support"
    MANAGER="manager"
    INVENTORY_OFFICER="inventory_officer"
    STOCK_MANAGER="stock_manager"
    USER="user"
class TicketStatus(str, enum.Enum):
    OPEN="Open"; IN_PROGRESS="In Progress"; WAITING="Waiting for User"; RESOLVED="Resolved"; CLOSED="Closed"
class Priority(str, enum.Enum):
    LOW="Low"; MEDIUM="Medium"; HIGH="High"; CRITICAL="Critical"

class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True)
    full_name: Mapped[str]=mapped_column(String(120))
    email: Mapped[str]=mapped_column(String(255),unique=True,index=True)
    password_hash: Mapped[str]=mapped_column(String(255))
    role: Mapped[UserRole]=mapped_column(Enum(UserRole),default=UserRole.USER,index=True)
    department: Mapped[str|None]=mapped_column(String(120),nullable=True)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    tickets: Mapped[list["Ticket"]]=relationship(back_populates="requester")
    profile_image: Mapped["UserProfileImage|None"]=relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    signature_image: Mapped["UserSignatureImage|None"]=relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def permissions(self) -> list[str]:
        from app.modules import permissions_for_role
        return sorted(permissions_for_role(self.role))

    @property
    def profile_picture_url(self) -> str | None:
        return f"/api/profile/picture/{self.id}" if self.profile_image else None

    @property
    def signature_image_url(self) -> str | None:
        return "/api/sign/profile/signature/file" if self.signature_image else None

class UserProfileImage(Base):
    __tablename__="user_profile_images"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id"),unique=True,index=True)
    stored_name: Mapped[str]=mapped_column(String(100),unique=True)
    mime_type: Mapped[str]=mapped_column(String(50))
    size_bytes: Mapped[int]=mapped_column()
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
    user: Mapped[User]=relationship(back_populates="profile_image")

class UserSignatureImage(Base):
    __tablename__="user_signature_images"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id"),unique=True,index=True)
    stored_name: Mapped[str]=mapped_column(String(100),unique=True)
    mime_type: Mapped[str]=mapped_column(String(50))
    size_bytes: Mapped[int]=mapped_column()
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
    user: Mapped[User]=relationship(back_populates="signature_image")

class Ticket(Base):
    __tablename__="tickets"
    id: Mapped[int]=mapped_column(primary_key=True)
    requester_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    full_name: Mapped[str]=mapped_column(String(120)); email: Mapped[str]=mapped_column(String(255))
    department: Mapped[str]=mapped_column(String(120)); location: Mapped[str]=mapped_column(String(120))
    device_name: Mapped[str|None]=mapped_column(String(120),nullable=True)
    title: Mapped[str]=mapped_column(String(200)); description: Mapped[str]=mapped_column(Text)
    urgency: Mapped[str]=mapped_column(String(30),default="Medium")
    attachment_url: Mapped[str|None]=mapped_column(String(500),nullable=True)
    category: Mapped[str]=mapped_column(String(80),default="Other",index=True)
    priority: Mapped[Priority]=mapped_column(Enum(Priority),default=Priority.MEDIUM,index=True)
    status: Mapped[TicketStatus]=mapped_column(Enum(TicketStatus),default=TicketStatus.OPEN,index=True)
    assigned_team: Mapped[str|None]=mapped_column(String(120),nullable=True)
    human_approval_required: Mapped[bool]=mapped_column(Boolean,default=False)
    human_approved: Mapped[bool]=mapped_column(Boolean,default=False)
    resolution_notes: Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
    requester: Mapped[User]=relationship(back_populates="tickets")
    ai_analysis: Mapped["TicketAIAnalysis|None"]=relationship(back_populates="ticket",uselist=False,cascade="all, delete-orphan")
    notes: Mapped[list["TicketNote"]]=relationship(back_populates="ticket",cascade="all, delete-orphan")
    attachments: Mapped[list["TicketAttachment"]]=relationship(back_populates="ticket",cascade="all, delete-orphan")
    messages: Mapped[list["TicketMessage"]]=relationship(back_populates="ticket",cascade="all, delete-orphan",order_by="TicketMessage.created_at")
    assignment: Mapped["TicketAssignment|None"]=relationship(back_populates="ticket",uselist=False,cascade="all, delete-orphan")
    intake_metadata: Mapped["TicketIntakeMetadata|None"]=relationship(back_populates="ticket",uselist=False,cascade="all, delete-orphan")
    video_links: Mapped[list["TicketVideoLink"]]=relationship(back_populates="ticket",cascade="all, delete-orphan")

    @property
    def assigned_user_id(self) -> int | None:
        return self.assignment.assignee_id if self.assignment else None

    @property
    def assigned_user_name(self) -> str | None:
        return self.assignment.assignee.full_name if self.assignment and self.assignment.assignee else None

    @property
    def requested_category(self) -> str | None:
        return self.intake_metadata.requested_category if self.intake_metadata else None

class TicketAIAnalysis(Base):
    __tablename__="ticket_ai_analyses"
    id: Mapped[int]=mapped_column(primary_key=True); ticket_id: Mapped[int]=mapped_column(ForeignKey("tickets.id"),unique=True)
    category: Mapped[str]=mapped_column(String(80)); priority: Mapped[str]=mapped_column(String(20)); summary: Mapped[str]=mapped_column(Text)
    possible_root_cause: Mapped[str]=mapped_column(Text); troubleshooting_steps: Mapped[list]=mapped_column(JSON)
    recommended_team: Mapped[str]=mapped_column(String(120)); needs_human_approval: Mapped[bool]=mapped_column(Boolean)
    suggested_user_reply: Mapped[str]=mapped_column(Text); confidence_score: Mapped[float]=mapped_column(Float)
    similar_issues: Mapped[list]=mapped_column(JSON,default=list); provider: Mapped[str]=mapped_column(String(40),default="rules")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    ticket: Mapped[Ticket]=relationship(back_populates="ai_analysis")

class TicketNote(Base):
    __tablename__="ticket_notes"
    id: Mapped[int]=mapped_column(primary_key=True); ticket_id: Mapped[int]=mapped_column(ForeignKey("tickets.id")); author_id: Mapped[int]=mapped_column(ForeignKey("users.id"))
    content: Mapped[str]=mapped_column(Text); is_internal: Mapped[bool]=mapped_column(Boolean,default=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    ticket: Mapped[Ticket]=relationship(back_populates="notes"); author: Mapped[User]=relationship()

class TicketMessage(Base):
    __tablename__="ticket_messages"
    id: Mapped[int]=mapped_column(primary_key=True)
    ticket_id: Mapped[int]=mapped_column(ForeignKey("tickets.id"),index=True)
    author_id: Mapped[int]=mapped_column(ForeignKey("users.id"))
    content: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    ticket: Mapped[Ticket]=relationship(back_populates="messages")
    author: Mapped[User]=relationship()

    @property
    def author_name(self) -> str:
        return self.author.full_name

    @property
    def author_role(self) -> str:
        return self.author.role.value

class TicketAssignment(Base):
    __tablename__="ticket_assignments"
    id: Mapped[int]=mapped_column(primary_key=True)
    ticket_id: Mapped[int]=mapped_column(ForeignKey("tickets.id"),unique=True,index=True)
    assignee_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    assigned_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"))
    assigned_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    ticket: Mapped[Ticket]=relationship(back_populates="assignment")
    assignee: Mapped[User]=relationship(foreign_keys=[assignee_id])
    assigned_by: Mapped[User]=relationship(foreign_keys=[assigned_by_id])

class TicketIntakeMetadata(Base):
    __tablename__="ticket_intake_metadata"
    id: Mapped[int]=mapped_column(primary_key=True)
    ticket_id: Mapped[int]=mapped_column(ForeignKey("tickets.id"),unique=True)
    requested_category: Mapped[str|None]=mapped_column(String(120),nullable=True)
    ticket: Mapped[Ticket]=relationship(back_populates="intake_metadata")

class TicketAttachment(Base):
    __tablename__="ticket_attachments"
    id: Mapped[int]=mapped_column(primary_key=True)
    ticket_id: Mapped[int]=mapped_column(ForeignKey("tickets.id"),index=True)
    uploader_id: Mapped[int]=mapped_column(ForeignKey("users.id"))
    original_name: Mapped[str]=mapped_column(String(255))
    stored_name: Mapped[str]=mapped_column(String(80),unique=True)
    mime_type: Mapped[str]=mapped_column(String(120))
    size_bytes: Mapped[int]=mapped_column()
    sha256: Mapped[str]=mapped_column(String(64))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    ticket: Mapped[Ticket]=relationship(back_populates="attachments")
    uploader: Mapped[User]=relationship()

    @property
    def download_url(self) -> str:
        return f"/api/tickets/{self.ticket_id}/attachments/{self.id}"

class KnowledgeBaseArticle(Base):
    __tablename__="knowledge_base_articles"
    id: Mapped[int]=mapped_column(primary_key=True); title: Mapped[str]=mapped_column(String(200)); category: Mapped[str]=mapped_column(String(80),index=True)
    problem_description: Mapped[str]=mapped_column(Text); solution: Mapped[str]=mapped_column(Text); tags: Mapped[list]=mapped_column(JSON,default=list)
    created_by_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,index=True)

class TicketCategory(Base):
    __tablename__="ticket_categories"
    id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]=mapped_column(String(80),unique=True); description: Mapped[str|None]=mapped_column(String(300),nullable=True); is_active: Mapped[bool]=mapped_column(Boolean,default=True)

class SupportLocation(Base):
    __tablename__="support_locations"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(120),unique=True)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True)
    sort_order: Mapped[int]=mapped_column(default=0)

class VideoArticle(Base):
    __tablename__="video_articles"
    id: Mapped[int]=mapped_column(primary_key=True)
    title: Mapped[str]=mapped_column(String(200))
    description: Mapped[str]=mapped_column(Text)
    url: Mapped[str]=mapped_column(String(1000))
    category: Mapped[str]=mapped_column(String(120))
    tags: Mapped[list]=mapped_column(JSON,default=list)
    duration_seconds: Mapped[int|None]=mapped_column(nullable=True)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True)
    created_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)

class TicketVideoLink(Base):
    __tablename__="ticket_video_links"
    id: Mapped[int]=mapped_column(primary_key=True)
    ticket_id: Mapped[int]=mapped_column(ForeignKey("tickets.id"),index=True)
    video_id: Mapped[int]=mapped_column(ForeignKey("video_articles.id"))
    recommended_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    ticket: Mapped[Ticket]=relationship(back_populates="video_links")
    video: Mapped[VideoArticle]=relationship()

class NotificationOutbox(Base):
    __tablename__="notification_outbox"
    id: Mapped[int]=mapped_column(primary_key=True)
    recipient: Mapped[str]=mapped_column(String(255),index=True)
    subject: Mapped[str]=mapped_column(String(255))
    body: Mapped[str]=mapped_column(Text)
    event_type: Mapped[str]=mapped_column(String(80),index=True)
    ticket_id: Mapped[int|None]=mapped_column(ForeignKey("tickets.id"),nullable=True,index=True)
    status: Mapped[str]=mapped_column(String(30),default="queued",index=True)
    attempts: Mapped[int]=mapped_column(default=0)
    last_error: Mapped[str|None]=mapped_column(String(500),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    sent_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)

class AuditLog(Base):
    __tablename__="audit_logs"
    id: Mapped[int]=mapped_column(primary_key=True); actor_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True); ticket_id: Mapped[int|None]=mapped_column(ForeignKey("tickets.id"),nullable=True,index=True)
    action: Mapped[str]=mapped_column(String(100),index=True); details: Mapped[dict]=mapped_column(JSON,default=dict); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)

class OrganizationSettings(Base):
    __tablename__="organization_settings"
    id: Mapped[int]=mapped_column(primary_key=True,default=1)
    organization_name: Mapped[str]=mapped_column(String(180),default="Mission Operations Portal")
    organization_short_name: Mapped[str]=mapped_column(String(80),default="Operations Portal")
    logo_stored_name: Mapped[str|None]=mapped_column(String(100),nullable=True)
    small_logo_stored_name: Mapped[str|None]=mapped_column(String(100),nullable=True)
    primary_color: Mapped[str]=mapped_column(String(20),default="#2563eb")
    theme_id: Mapped[str]=mapped_column(String(40),default="operations-blue")
    support_email: Mapped[str|None]=mapped_column(String(255),nullable=True)
    address: Mapped[str|None]=mapped_column(String(500),nullable=True)
    footer_text: Mapped[str|None]=mapped_column(String(255),nullable=True)
    updated_by: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,index=True)
    @property
    def logo_url(self) -> str | None:
        return "/api/organization-settings/logo/file" if self.logo_stored_name else None
    @property
    def small_logo_url(self) -> str | None:
        return "/api/organization-settings/small-logo/file" if self.small_logo_stored_name else None
    @property
    def collapsed_sidebar_icon_url(self) -> str | None:
        return "/api/organization-settings/collapsed-sidebar-icon/file" if self.small_logo_stored_name else None

class InventoryItem(Base):
    __tablename__="inventory_items"
    id: Mapped[int]=mapped_column(primary_key=True)
    status: Mapped[str]=mapped_column(String(80),default="In Stock",index=True)
    country: Mapped[str|None]=mapped_column(String(120),nullable=True)
    project: Mapped[str|None]=mapped_column(String(120),nullable=True)
    category: Mapped[str]=mapped_column(String(120),index=True)
    sub_category: Mapped[str|None]=mapped_column(String(120),nullable=True)
    number: Mapped[str|None]=mapped_column(String(80),nullable=True)
    donor: Mapped[str|None]=mapped_column(String(120),nullable=True)
    owner: Mapped[str|None]=mapped_column(String(180),nullable=True)
    designation: Mapped[str]=mapped_column(String(220),index=True)
    brand: Mapped[str|None]=mapped_column(String(120),nullable=True)
    model: Mapped[str|None]=mapped_column(String(120),nullable=True)
    serial_number: Mapped[str|None]=mapped_column(String(160),nullable=True,index=True)
    pr_reference: Mapped[str|None]=mapped_column(String(120),nullable=True)
    location: Mapped[str]=mapped_column(String(180),index=True)
    user_name: Mapped[str|None]=mapped_column(String(180),nullable=True,index=True)
    assigned_user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True)
    date_last_inventory: Mapped[str|None]=mapped_column(String(40),nullable=True)
    purchasing_date: Mapped[str|None]=mapped_column(String(40),nullable=True)
    supplier: Mapped[str|None]=mapped_column(String(180),nullable=True)
    purchase_value: Mapped[str|None]=mapped_column(String(80),nullable=True)
    currency: Mapped[str|None]=mapped_column(String(20),nullable=True)
    purchase_value_euros: Mapped[str|None]=mapped_column(String(80),nullable=True)
    depreciation_period: Mapped[str|None]=mapped_column(String(80),nullable=True)
    months_since_purchasing: Mapped[str|None]=mapped_column(String(80),nullable=True)
    current_value_euros: Mapped[str|None]=mapped_column(String(80),nullable=True)
    accessories: Mapped[str|None]=mapped_column(Text,nullable=True)
    condition: Mapped[str|None]=mapped_column(String(120),nullable=True)
    remarks: Mapped[str|None]=mapped_column(Text,nullable=True)
    outing_date: Mapped[str|None]=mapped_column(String(40),nullable=True)
    reason: Mapped[str|None]=mapped_column(Text,nullable=True)
    additional_comments: Mapped[str|None]=mapped_column(Text,nullable=True)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    created_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,index=True)
    assigned_user: Mapped[User|None]=relationship(foreign_keys=[assigned_user_id])
    @property
    def assigned_user_name(self) -> str | None:
        return self.assigned_user.full_name if self.assigned_user else self.user_name
    @property
    def logistics_code(self) -> str:
        return "/".join(filter(None, [self.country, self.project, self.category, self.sub_category, self.number]))

class StockCategory(Base):
    __tablename__="stock_categories"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(120),unique=True,index=True)
    description: Mapped[str|None]=mapped_column(String(500),nullable=True)
    icon: Mapped[str]=mapped_column(String(80),default="Package")
    display_order: Mapped[int]=mapped_column(default=0,index=True)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    created_by_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True)
    updated_by_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,index=True)
    items: Mapped[list["StockItem"]]=relationship(back_populates="category_record")
    @property
    def item_count(self) -> int:
        return len([item for item in self.items if item.is_active])

class StockItem(Base):
    __tablename__="stock_items"
    id: Mapped[int]=mapped_column(primary_key=True)
    item_name: Mapped[str]=mapped_column(String(180),index=True)
    category: Mapped[str]=mapped_column(String(120),index=True)
    category_id: Mapped[int|None]=mapped_column(ForeignKey("stock_categories.id"),nullable=True,index=True)
    item_type: Mapped[str|None]=mapped_column(String(120),nullable=True,index=True)
    specifications: Mapped[str|None]=mapped_column(Text,nullable=True)
    quantity_available: Mapped[int]=mapped_column(default=0)
    low_stock_threshold: Mapped[int]=mapped_column(default=5)
    unit: Mapped[str]=mapped_column(String(50),default="piece")
    donor: Mapped[str|None]=mapped_column(String(120),nullable=True,index=True)
    project_code: Mapped[str|None]=mapped_column(String(120),nullable=True,index=True)
    unit_price: Mapped[float]=mapped_column(Float,default=0)
    currency: Mapped[str]=mapped_column(String(20),default="AFN")
    expiration_date: Mapped[datetime|None]=mapped_column(Date,nullable=True)
    picture_stored_name: Mapped[str|None]=mapped_column(String(100),nullable=True)
    location: Mapped[str]=mapped_column(String(180),index=True)
    responsible_person_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True)
    status: Mapped[str]=mapped_column(String(40),default="Available",index=True)
    notes: Mapped[str|None]=mapped_column(Text,nullable=True)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,index=True)
    responsible_person: Mapped[User|None]=relationship(foreign_keys=[responsible_person_id])
    category_record: Mapped[StockCategory|None]=relationship(back_populates="items")
    @property
    def responsible_person_name(self) -> str | None:
        return self.responsible_person.full_name if self.responsible_person else None
    @property
    def picture_url(self) -> str | None:
        return f"/api/stock/items/{self.id}/picture" if self.picture_stored_name else None
    @property
    def category_name(self) -> str:
        return self.category_record.name if self.category_record else self.category

class StockRequest(Base):
    __tablename__="stock_requests"
    id: Mapped[int]=mapped_column(primary_key=True)
    request_number: Mapped[str]=mapped_column(String(40),unique=True,index=True)
    requested_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    department: Mapped[str|None]=mapped_column(String(120),nullable=True)
    location: Mapped[str]=mapped_column(String(180),index=True)
    item_id: Mapped[int]=mapped_column(ForeignKey("stock_items.id"),index=True)
    requested_quantity: Mapped[int]=mapped_column()
    reason: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(40),default="Pending",index=True)
    approved_by_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True)
    delivered_by_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True)
    notes: Mapped[str|None]=mapped_column(Text,nullable=True)
    request_date: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    decision_date: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    delivery_date: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,index=True)
    requested_by: Mapped[User]=relationship(foreign_keys=[requested_by_id])
    item: Mapped[StockItem]=relationship()
    approved_by: Mapped[User|None]=relationship(foreign_keys=[approved_by_id])
    delivered_by: Mapped[User|None]=relationship(foreign_keys=[delivered_by_id])
    history: Mapped[list["StockRequestStatusHistory"]]=relationship(cascade="all, delete-orphan")
    @property
    def requested_by_name(self) -> str:
        return self.requested_by.full_name
    @property
    def item_name(self) -> str:
        return self.item.item_name
    @property
    def approved_by_name(self) -> str | None:
        return self.approved_by.full_name if self.approved_by else None
    @property
    def delivered_by_name(self) -> str | None:
        return self.delivered_by.full_name if self.delivered_by else None

class StockRequestStatusHistory(Base):
    __tablename__="stock_request_status_history"
    id: Mapped[int]=mapped_column(primary_key=True)
    request_id: Mapped[int]=mapped_column(ForeignKey("stock_requests.id"),index=True)
    status: Mapped[str]=mapped_column(String(40),index=True)
    changed_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    note: Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)

class StockMovement(Base):
    __tablename__="stock_movements"
    id: Mapped[int]=mapped_column(primary_key=True)
    stock_item_id: Mapped[int]=mapped_column(ForeignKey("stock_items.id"),index=True)
    stock_card_id: Mapped[int|None]=mapped_column(ForeignKey("stock_cards.id"),nullable=True,index=True)
    stock_request_id: Mapped[int|None]=mapped_column(ForeignKey("stock_requests.id"),nullable=True,index=True)
    movement_type: Mapped[str]=mapped_column(String(40),index=True)
    quantity_change: Mapped[int]=mapped_column()
    performed_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    movement_date: Mapped[datetime]=mapped_column(Date,default=lambda: utcnow().date(),index=True)
    month_number: Mapped[int]=mapped_column(default=1,index=True)
    year: Mapped[int]=mapped_column(default=lambda: utcnow().year,index=True)
    quantity_in: Mapped[float]=mapped_column(Float,default=0)
    quantity_out: Mapped[float]=mapped_column(Float,default=0)
    po_number: Mapped[str|None]=mapped_column(String(120),nullable=True)
    waybill_number: Mapped[str|None]=mapped_column(String(120),nullable=True)
    goods_received_note_no: Mapped[str|None]=mapped_column(String(120),nullable=True)
    stock_transfer_no: Mapped[str|None]=mapped_column(String(120),nullable=True)
    destination: Mapped[str|None]=mapped_column(String(250),nullable=True)
    remarks: Mapped[str|None]=mapped_column(Text,nullable=True)
    comments: Mapped[str|None]=mapped_column(Text,nullable=True)
    signature_name: Mapped[str|None]=mapped_column(String(160),nullable=True)
    mission: Mapped[str]=mapped_column(String(120),default="DEMO MISSION",index=True)
    base: Mapped[str]=mapped_column(String(120),default="COORDINATION",index=True)
    source_reference_type: Mapped[str|None]=mapped_column(String(80),nullable=True)
    source_reference_id: Mapped[int|None]=mapped_column(nullable=True,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,index=True)
    item: Mapped[StockItem]=relationship()
    stock_card: Mapped["StockCard|None"]=relationship(back_populates="movements")

class StockCard(Base):
    __tablename__="stock_cards"
    id: Mapped[int]=mapped_column(primary_key=True)
    base: Mapped[str]=mapped_column(String(3),index=True)
    storage_location: Mapped[str]=mapped_column(String(3),index=True)
    sequence_number: Mapped[str]=mapped_column(String(3),index=True)
    stock_card_number: Mapped[str]=mapped_column(String(20),unique=True,index=True)
    donor: Mapped[str|None]=mapped_column(String(120),nullable=True,index=True)
    project_code: Mapped[str|None]=mapped_column(String(120),nullable=True,index=True)
    stock_item_id: Mapped[int]=mapped_column(ForeignKey("stock_items.id"),index=True)
    specifications: Mapped[str|None]=mapped_column(Text,nullable=True)
    unit: Mapped[str]=mapped_column(String(50))
    expiration_date: Mapped[datetime|None]=mapped_column(Date,nullable=True)
    unit_price: Mapped[float]=mapped_column(Float,default=0)
    currency: Mapped[str]=mapped_column(String(20),default="AFN")
    comments: Mapped[str|None]=mapped_column(Text,nullable=True)
    opening_quantity: Mapped[float]=mapped_column(Float,default=0)
    minimum_quantity: Mapped[float]=mapped_column(Float,default=0)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    created_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,index=True)
    item: Mapped[StockItem]=relationship()
    movements: Mapped[list[StockMovement]]=relationship(back_populates="stock_card")
    @property
    def item_name(self) -> str:
        return self.item.item_name

class PhysicalInventoryCount(Base):
    __tablename__="physical_inventory_counts"
    id: Mapped[int]=mapped_column(primary_key=True)
    stock_item_id: Mapped[int]=mapped_column(ForeignKey("stock_items.id"),index=True)
    stock_card_id: Mapped[int|None]=mapped_column(ForeignKey("stock_cards.id"),nullable=True,index=True)
    count_date: Mapped[datetime]=mapped_column(Date,index=True)
    year: Mapped[int]=mapped_column(index=True)
    month_number: Mapped[int]=mapped_column(index=True)
    physical_quantity: Mapped[float]=mapped_column(Float)
    counted_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    notes: Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,index=True)

class Dashboard(Base):
    __tablename__="dashboards"
    id: Mapped[int]=mapped_column(primary_key=True)
    title: Mapped[str]=mapped_column(String(180),index=True)
    description: Mapped[str|None]=mapped_column(Text,nullable=True)
    embed_url: Mapped[str]=mapped_column(String(1200))
    provider: Mapped[str]=mapped_column(String(50),default="Power BI")
    is_active: Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    allowed_roles: Mapped[list]=mapped_column(JSON,default=list)
    created_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    updated_by_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,index=True)
    accesses: Mapped[list["DashboardAccess"]]=relationship(back_populates="dashboard",cascade="all, delete-orphan")
    @property
    def user_ids(self) -> list[int]:
        return [access.user_id for access in self.accesses if access.can_view]

class DashboardAccess(Base):
    __tablename__="dashboard_access"
    id: Mapped[int]=mapped_column(primary_key=True)
    dashboard_id: Mapped[int]=mapped_column(ForeignKey("dashboards.id"),index=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    can_view: Mapped[bool]=mapped_column(Boolean,default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    dashboard: Mapped[Dashboard]=relationship(back_populates="accesses")

class SignatureEnvelope(Base):
    __tablename__="signature_envelopes"
    id: Mapped[int]=mapped_column(primary_key=True)
    envelope_id: Mapped[str]=mapped_column(String(30),unique=True,index=True)
    document_type: Mapped[str]=mapped_column(String(60),index=True)
    document_reference_id: Mapped[str|None]=mapped_column(String(120),nullable=True,index=True)
    title: Mapped[str]=mapped_column(String(220),index=True)
    subject: Mapped[str|None]=mapped_column(String(255),nullable=True)
    message: Mapped[str|None]=mapped_column(Text,nullable=True)
    status: Mapped[str]=mapped_column(String(40),default="draft",index=True)
    routing_mode: Mapped[str]=mapped_column(String(20),default="sequential")
    original_pdf_path: Mapped[str]=mapped_column(String(180))
    original_pdf_hash: Mapped[str]=mapped_column(String(64),index=True)
    current_document_hash: Mapped[str]=mapped_column(String(64),index=True)
    final_signed_pdf_path: Mapped[str|None]=mapped_column(String(180),nullable=True)
    final_signed_pdf_hash: Mapped[str|None]=mapped_column(String(64),nullable=True,index=True)
    created_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,index=True)
    recipients: Mapped[list["SignatureRecipient"]]=relationship(back_populates="envelope",cascade="all, delete-orphan",order_by="SignatureRecipient.routing_order")

class SignatureRecipient(Base):
    __tablename__="signature_recipients"
    id: Mapped[int]=mapped_column(primary_key=True)
    envelope_db_id: Mapped[int]=mapped_column(ForeignKey("signature_envelopes.id"),index=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    full_name: Mapped[str]=mapped_column(String(120))
    email: Mapped[str]=mapped_column(String(255),index=True)
    role_name: Mapped[str|None]=mapped_column(String(120),nullable=True)
    routing_order: Mapped[int]=mapped_column(index=True)
    signature_page: Mapped[int]=mapped_column(default=-1)
    signature_x: Mapped[float]=mapped_column(Float,default=0.61)
    signature_y: Mapped[float]=mapped_column(Float,default=0.06)
    signature_width: Mapped[float]=mapped_column(Float,default=0.32)
    signature_height: Mapped[float]=mapped_column(Float,default=0.16)
    status: Mapped[str]=mapped_column(String(30),default="pending",index=True)
    verification_number: Mapped[str|None]=mapped_column(String(30),nullable=True,unique=True,index=True)
    signature_image_path_snapshot: Mapped[str|None]=mapped_column(String(180),nullable=True)
    signed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    viewed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    ip_address: Mapped[str|None]=mapped_column(String(80),nullable=True)
    user_agent: Mapped[str|None]=mapped_column(String(500),nullable=True)
    comment: Mapped[str|None]=mapped_column(Text,nullable=True)
    document_hash_at_action: Mapped[str|None]=mapped_column(String(64),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,index=True)
    envelope: Mapped[SignatureEnvelope]=relationship(back_populates="recipients")
    user: Mapped[User]=relationship(foreign_keys=[user_id])

class SignatureToken(Base):
    __tablename__="signature_tokens"
    id: Mapped[int]=mapped_column(primary_key=True)
    envelope_db_id: Mapped[int]=mapped_column(ForeignKey("signature_envelopes.id"),index=True)
    recipient_id: Mapped[int]=mapped_column(ForeignKey("signature_recipients.id"),index=True)
    token_hash: Mapped[str]=mapped_column(String(64),unique=True,index=True)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True)
    used_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    is_revoked: Mapped[bool]=mapped_column(Boolean,default=False,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)

class SignedDocument(Base):
    __tablename__="signed_documents"
    id: Mapped[int]=mapped_column(primary_key=True)
    envelope_db_id: Mapped[int]=mapped_column(ForeignKey("signature_envelopes.id"),index=True)
    version_number: Mapped[int]=mapped_column(index=True)
    file_path: Mapped[str]=mapped_column(String(180))
    file_hash: Mapped[str]=mapped_column(String(64),index=True)
    created_after_recipient_id: Mapped[int|None]=mapped_column(ForeignKey("signature_recipients.id"),nullable=True,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)

class SignatureAuditLog(Base):
    __tablename__="signature_audit_logs"
    id: Mapped[int]=mapped_column(primary_key=True)
    envelope_db_id: Mapped[int]=mapped_column(ForeignKey("signature_envelopes.id"),index=True)
    recipient_id: Mapped[int|None]=mapped_column(ForeignKey("signature_recipients.id"),nullable=True,index=True)
    user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True)
    action: Mapped[str]=mapped_column(String(100),index=True)
    details: Mapped[dict]=mapped_column(JSON,default=dict)
    ip_address: Mapped[str|None]=mapped_column(String(80),nullable=True)
    user_agent: Mapped[str|None]=mapped_column(String(500),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)

class FazaSignSettings(Base):
    __tablename__="faza_sign_settings"
    id: Mapped[int]=mapped_column(primary_key=True,default=1)
    is_enabled: Mapped[bool]=mapped_column(Boolean,default=True)
    require_signature_image: Mapped[bool]=mapped_column(Boolean,default=False)
    default_token_expiry_hours: Mapped[int]=mapped_column(default=72)
    allow_public_verification: Mapped[bool]=mapped_column(Boolean,default=False)
    default_routing_mode: Mapped[str]=mapped_column(String(20),default="sequential")
    email_notification_enabled: Mapped[bool]=mapped_column(Boolean,default=True)
    signature_stamp_position: Mapped[str]=mapped_column(String(30),default="signature_page")
    max_signature_image_size: Mapped[int]=mapped_column(default=3_145_728)
    allowed_signature_image_types: Mapped[list]=mapped_column(JSON,default=lambda:["image/png","image/jpeg","image/webp"])
    updated_by_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)

class LanConversation(Base):
    __tablename__="lan_conversations"
    id: Mapped[int]=mapped_column(primary_key=True)
    type: Mapped[str]=mapped_column(String(20),index=True)
    name: Mapped[str|None]=mapped_column(String(180),nullable=True,index=True)
    description: Mapped[str|None]=mapped_column(Text,nullable=True)
    avatar_url: Mapped[str|None]=mapped_column(String(500),nullable=True)
    is_private: Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    created_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,index=True)
    members: Mapped[list["LanConversationMember"]]=relationship(back_populates="conversation",cascade="all, delete-orphan")
    messages: Mapped[list["LanMessage"]]=relationship(back_populates="conversation",cascade="all, delete-orphan")

class LanConversationMember(Base):
    __tablename__="lan_conversation_members"
    id: Mapped[int]=mapped_column(primary_key=True)
    conversation_id: Mapped[int]=mapped_column(ForeignKey("lan_conversations.id"),index=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    role: Mapped[str]=mapped_column(String(20),default="member")
    joined_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    last_read_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    is_muted: Mapped[bool]=mapped_column(Boolean,default=False)
    conversation: Mapped[LanConversation]=relationship(back_populates="members")
    user: Mapped[User]=relationship()

class LanMessage(Base):
    __tablename__="lan_messages"
    id: Mapped[int]=mapped_column(primary_key=True)
    conversation_id: Mapped[int]=mapped_column(ForeignKey("lan_conversations.id"),index=True)
    sender_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    content: Mapped[str]=mapped_column(Text,default="")
    message_type: Mapped[str]=mapped_column(String(20),default="text",index=True)
    parent_message_id: Mapped[int|None]=mapped_column(ForeignKey("lan_messages.id"),nullable=True,index=True)
    is_edited: Mapped[bool]=mapped_column(Boolean,default=False)
    is_deleted: Mapped[bool]=mapped_column(Boolean,default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
    conversation: Mapped[LanConversation]=relationship(back_populates="messages")
    sender: Mapped[User]=relationship(foreign_keys=[sender_id])
    attachments: Mapped[list["LanAttachment"]]=relationship(back_populates="message",cascade="all, delete-orphan")

class LanAttachment(Base):
    __tablename__="lan_attachments"
    id: Mapped[int]=mapped_column(primary_key=True)
    message_id: Mapped[int]=mapped_column(ForeignKey("lan_messages.id"),index=True)
    uploaded_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    original_filename: Mapped[str]=mapped_column(String(255))
    stored_filename: Mapped[str]=mapped_column(String(100),unique=True)
    mime_type: Mapped[str]=mapped_column(String(120))
    file_size: Mapped[int]=mapped_column()
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    message: Mapped[LanMessage]=relationship(back_populates="attachments")

class LanMeeting(Base):
    __tablename__="lan_meetings"
    id: Mapped[int]=mapped_column(primary_key=True)
    title: Mapped[str]=mapped_column(String(200),index=True)
    description: Mapped[str|None]=mapped_column(Text,nullable=True)
    meeting_type: Mapped[str]=mapped_column(String(20),index=True)
    conversation_id: Mapped[int|None]=mapped_column(ForeignKey("lan_conversations.id"),nullable=True,index=True)
    scheduled_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    start_time: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True)
    end_time: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True)
    status: Mapped[str]=mapped_column(String(20),default="scheduled",index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
    participants: Mapped[list["LanMeetingParticipant"]]=relationship(back_populates="meeting",cascade="all, delete-orphan")

class LanMeetingParticipant(Base):
    __tablename__="lan_meeting_participants"
    id: Mapped[int]=mapped_column(primary_key=True)
    meeting_id: Mapped[int]=mapped_column(ForeignKey("lan_meetings.id"),index=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    status: Mapped[str]=mapped_column(String(20),default="invited")
    joined_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    left_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    meeting: Mapped[LanMeeting]=relationship(back_populates="participants")
    user: Mapped[User]=relationship()

class LanCallSession(Base):
    __tablename__="lan_call_sessions"
    id: Mapped[int]=mapped_column(primary_key=True)
    conversation_id: Mapped[int|None]=mapped_column(ForeignKey("lan_conversations.id"),nullable=True,index=True)
    meeting_id: Mapped[int|None]=mapped_column(ForeignKey("lan_meetings.id"),nullable=True,index=True)
    started_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    call_type: Mapped[str]=mapped_column(String(20),index=True)
    call_scope: Mapped[str]=mapped_column(String(20),index=True)
    status: Mapped[str]=mapped_column(String(20),default="started",index=True)
    started_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    ended_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    participants: Mapped[list["LanCallParticipant"]]=relationship(back_populates="call",cascade="all, delete-orphan")

class LanCallParticipant(Base):
    __tablename__="lan_call_participants"
    id: Mapped[int]=mapped_column(primary_key=True)
    call_session_id: Mapped[int]=mapped_column(ForeignKey("lan_call_sessions.id"),index=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    status: Mapped[str]=mapped_column(String(20),default="invited",index=True)
    joined_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    left_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    is_muted: Mapped[bool]=mapped_column(Boolean,default=False)
    is_video_enabled: Mapped[bool]=mapped_column(Boolean,default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
    call: Mapped[LanCallSession]=relationship(back_populates="participants")
    user: Mapped[User]=relationship()

class LanMessengerSettings(Base):
    __tablename__="lan_messenger_settings"
    id: Mapped[int]=mapped_column(primary_key=True,default=1)
    enabled: Mapped[bool]=mapped_column(Boolean,default=True)
    internal_lan_base_url: Mapped[str|None]=mapped_column(String(500),nullable=True)
    public_base_url: Mapped[str|None]=mapped_column(String(500),nullable=True)
    lan_cidrs: Mapped[list]=mapped_column(JSON,default=lambda:["192.168.0.0/16","10.0.0.0/8","172.16.0.0/12"])
    prefer_lan_for_private_ips: Mapped[bool]=mapped_column(Boolean,default=True)
    allow_external_access: Mapped[bool]=mapped_column(Boolean,default=True)
    allow_direct_messages: Mapped[bool]=mapped_column(Boolean,default=True)
    allow_groups: Mapped[bool]=mapped_column(Boolean,default=True)
    allow_channels: Mapped[bool]=mapped_column(Boolean,default=True)
    allow_meetings: Mapped[bool]=mapped_column(Boolean,default=True)
    allow_file_uploads: Mapped[bool]=mapped_column(Boolean,default=True)
    allow_voice_calls: Mapped[bool]=mapped_column(Boolean,default=True)
    allow_video_calls: Mapped[bool]=mapped_column(Boolean,default=True)
    allow_group_voice_calls: Mapped[bool]=mapped_column(Boolean,default=True)
    allow_group_video_calls: Mapped[bool]=mapped_column(Boolean,default=True)
    allow_meeting_calls: Mapped[bool]=mapped_column(Boolean,default=True)
    max_file_size_mb: Mapped[int]=mapped_column(default=10)
    updated_by_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)

