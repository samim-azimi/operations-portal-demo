from datetime import date, datetime
from typing import Generic, Literal, TypeVar
from pydantic import BaseModel,ConfigDict,EmailStr,Field,HttpUrl
from app.models import Priority,TicketStatus,UserRole

T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    items:list[T]
    total:int
    page:int
    page_size:int
    pages:int

class UserBase(BaseModel):
    full_name:str=Field(min_length=2,max_length=120); email:EmailStr; role:UserRole=UserRole.USER; department:str|None=None; is_active:bool=True
class UserCreate(UserBase): password:str=Field(min_length=12,max_length=128)
class UserUpdate(BaseModel):
    full_name:str|None=Field(default=None,min_length=2,max_length=120)
    email:EmailStr|None=None
    role:UserRole|None=None
    department:str|None=Field(default=None,max_length=120)
    is_active:bool|None=None
class UserRead(UserBase):
    id:int; created_at:datetime; permissions:list[str]=[]; profile_picture_url:str|None=None; signature_image_url:str|None=None
    model_config=ConfigDict(from_attributes=True)
class Token(BaseModel): access_token:str; token_type:str="bearer"; user:UserRead
class TicketCreate(BaseModel):
    location:str=Field(min_length=2,max_length=120)
    category:str|None=Field(default=None,max_length=120)
    device_name:str|None=Field(default=None,max_length=120); title:str=Field(min_length=4,max_length=200); description:str=Field(min_length=10,max_length=10000)
    urgency:Literal["Low","Medium","High","Critical"]="Medium"; attachment_url:str|None=Field(default=None,max_length=500)
class AIAnalysisRead(BaseModel):
    id:int; category:str; priority:str; summary:str; possible_root_cause:str; troubleshooting_steps:list[str]; recommended_team:str; needs_human_approval:bool
    suggested_user_reply:str; confidence_score:float; similar_issues:list[dict]; provider:str; created_at:datetime
    model_config=ConfigDict(from_attributes=True)
class NoteCreate(BaseModel): content:str=Field(min_length=2,max_length=5000); is_internal:bool=True
class NoteRead(BaseModel):
    id:int; author_id:int; content:str; is_internal:bool; created_at:datetime
    model_config=ConfigDict(from_attributes=True)
class MessageCreate(BaseModel): content:str=Field(min_length=1,max_length=5000)
class MessageRead(BaseModel):
    id:int; author_id:int; author_name:str; author_role:str; content:str; created_at:datetime
    model_config=ConfigDict(from_attributes=True)
class AttachmentRead(BaseModel):
    id:int; original_name:str; mime_type:str; size_bytes:int; sha256:str; created_at:datetime
    download_url:str|None=None
    model_config=ConfigDict(from_attributes=True)
class TicketUpdate(BaseModel):
    category:str|None=None; priority:Priority|None=None; status:TicketStatus|None=None; assigned_team:str|None=None; assigned_user_id:int|None=None; resolution_notes:str|None=None; accept_ai_recommendation:bool=False; human_approved:bool|None=None
class TicketRead(BaseModel):
    id:int; requester_id:int; full_name:str; email:EmailStr; department:str; location:str; device_name:str|None; title:str; description:str; urgency:str; attachment_url:str|None
    category:str; requested_category:str|None=None; priority:Priority; status:TicketStatus; assigned_team:str|None; assigned_user_id:int|None=None; assigned_user_name:str|None=None; human_approval_required:bool; human_approved:bool; resolution_notes:str|None
    created_at:datetime; updated_at:datetime; ai_analysis:AIAnalysisRead|None=None; notes:list[NoteRead]=[]; attachments:list[AttachmentRead]=[]; messages:list[MessageRead]=[]
    model_config=ConfigDict(from_attributes=True)
class KbCreate(BaseModel):
    title:str=Field(min_length=3,max_length=200); category:str=Field(min_length=2,max_length=80); problem_description:str=Field(min_length=5,max_length=10000); solution:str=Field(min_length=5,max_length=20000); tags:list[str]=Field(default_factory=list,max_length=20)
class KbRead(KbCreate):
    id:int; created_by_id:int|None; created_at:datetime; updated_at:datetime
    model_config=ConfigDict(from_attributes=True)
class DashboardStats(BaseModel):
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    closed_tickets: int
    critical_tickets: int
    high_risk_tickets: int
    pending_approval: int
    low_confidence_tickets: int
    unassigned_tickets: int
    average_ai_confidence: float
    automation_coverage: float
    by_category: dict[str, int]
    by_priority: dict[str, int]
    by_status: dict[str, int]
    by_team: dict[str, int]
    recent_tickets: list[TicketRead]

class CategoryCreate(BaseModel): name:str=Field(min_length=2,max_length=80); description:str|None=None; is_active:bool=True
class CategoryRead(CategoryCreate):
    id:int
    model_config=ConfigDict(from_attributes=True)
class LocationCreate(BaseModel):
    name:str=Field(min_length=2,max_length=120); is_active:bool=True; sort_order:int=0
class LocationRead(LocationCreate):
    id:int
    model_config=ConfigDict(from_attributes=True)
class VideoCreate(BaseModel):
    title:str=Field(min_length=3,max_length=200)
    description:str=Field(min_length=5,max_length=5000)
    url:HttpUrl
    category:str=Field(min_length=2,max_length=120)
    tags:list[str]=Field(default_factory=list,max_length=20)
    duration_seconds:int|None=Field(default=None,ge=1,le=86400)
    is_active:bool=True
class VideoRead(VideoCreate):
    id:int; created_by_id:int; created_at:datetime; updated_at:datetime
    model_config=ConfigDict(from_attributes=True)
class BulkImportRow(BaseModel):
    row:int; email:EmailStr; temporary_password:str|None=None; status:str; detail:str|None=None
class BulkImportResult(BaseModel):
    created:int; skipped:int; failed:int; rows:list[BulkImportRow]
class NotificationRead(BaseModel):
    id:int; recipient:EmailStr; subject:str; event_type:str; ticket_id:int|None; status:str; attempts:int; last_error:str|None; created_at:datetime; sent_at:datetime|None
    model_config=ConfigDict(from_attributes=True)
class ModuleRead(BaseModel):
    id:str; name:str; short_name:str; description:str; icon:str; route:str
    status:Literal["active","coming_soon","hidden"]
    required_permission:str; category:str
class WorkspaceActivityRead(BaseModel):
    id:int; title:str; status:str; updated_at:datetime; module:str="helpdesk"
class WorkspaceSummary(BaseModel):
    accessible_modules:int; active_modules:int; open_helpdesk_tickets:int|None
    notification_count:int; recent_activity:list[WorkspaceActivityRead]
    my_asset_count:int=0; my_stock_request_count:int=0; my_ticket_count:int=0
    module_insights:dict[str,dict[str,int]]=Field(default_factory=dict)
class AuditLogRead(BaseModel):
    id:int; actor_id:int|None; ticket_id:int|None; action:str; details:dict; created_at:datetime
    model_config=ConfigDict(from_attributes=True)
class TaskRead(BaseModel):
    id:int; title:str; status:str; created_at:datetime

class OrganizationSettingsUpdate(BaseModel):
    organization_name:str=Field(min_length=2,max_length=180)
    organization_short_name:str=Field(min_length=1,max_length=80)
    primary_color:str=Field(default="#2563eb",pattern=r"^#[0-9A-Fa-f]{6}$")
    theme_id:str=Field(default="operations-blue",max_length=40)
    support_email:EmailStr|None=None
    address:str|None=Field(default=None,max_length=500)
    footer_text:str|None=Field(default=None,max_length=255)

class OrganizationSettingsRead(OrganizationSettingsUpdate):
    id:int; logo_url:str|None=None; small_logo_url:str|None=None
    collapsed_sidebar_icon_url:str|None=None; updated_at:datetime
    model_config=ConfigDict(from_attributes=True)

class InventoryItemBase(BaseModel):
    status:Literal["In Stock","Allocated","Out of Inventory"]="In Stock"
    country:str|None=Field(default="Demo Country",max_length=120)
    project:str|None=Field(default=None,max_length=120)
    category:str=Field(min_length=1,max_length=120)
    sub_category:str|None=Field(default=None,max_length=120)
    number:str|None=Field(default=None,max_length=80)
    donor:str|None=Field(default=None,max_length=120)
    owner:str|None=Field(default=None,max_length=180)
    designation:str=Field(min_length=1,max_length=220)
    brand:str|None=Field(default=None,max_length=120)
    model:str|None=Field(default=None,max_length=120)
    serial_number:str|None=Field(default=None,max_length=160)
    pr_reference:str|None=Field(default=None,max_length=120)
    location:str=Field(min_length=1,max_length=180)
    user_name:str|None=Field(default=None,max_length=180)
    assigned_user_id:int|None=None
    date_last_inventory:str|None=Field(default=None,max_length=40)
    purchasing_date:str|None=Field(default=None,max_length=40)
    supplier:str|None=Field(default=None,max_length=180)
    purchase_value:str|None=Field(default=None,max_length=80)
    currency:str|None=Field(default=None,max_length=20)
    purchase_value_euros:str|None=Field(default=None,max_length=80)
    depreciation_period:str|None=Field(default=None,max_length=80)
    months_since_purchasing:str|None=Field(default=None,max_length=80)
    current_value_euros:str|None=Field(default=None,max_length=80)
    accessories:str|None=None
    condition:str|None=Field(default=None,max_length=120)
    remarks:str|None=None
    outing_date:str|None=Field(default=None,max_length=40)
    reason:str|None=None
    additional_comments:str|None=None

class InventoryItemCreate(InventoryItemBase): pass
class InventoryItemUpdate(BaseModel):
    status:Literal["In Stock","Allocated","Out of Inventory"]|None=None; country:str|None=None; project:str|None=None; category:str|None=None
    sub_category:str|None=None; number:str|None=None; donor:str|None=None; owner:str|None=None
    designation:str|None=None; brand:str|None=None; model:str|None=None; serial_number:str|None=None
    pr_reference:str|None=None; location:str|None=None; user_name:str|None=None; assigned_user_id:int|None=None
    date_last_inventory:str|None=None; purchasing_date:str|None=None; supplier:str|None=None
    purchase_value:str|None=None; currency:str|None=None; purchase_value_euros:str|None=None
    depreciation_period:str|None=None; months_since_purchasing:str|None=None; current_value_euros:str|None=None
    accessories:str|None=None; condition:str|None=None; remarks:str|None=None; outing_date:str|None=None
    reason:str|None=None; additional_comments:str|None=None; is_active:bool|None=None
class InventoryItemRead(InventoryItemBase):
    id:int; is_active:bool; created_by_id:int; created_at:datetime; updated_at:datetime
    assigned_user_name:str|None=None; logistics_code:str
    model_config=ConfigDict(from_attributes=True)

class InventoryImportRow(BaseModel):
    row:int
    status:Literal["valid","invalid","imported","skipped"]
    detail:str|None=None
    warnings:list[str]=Field(default_factory=list)
    data:dict=Field(default_factory=dict)

class InventoryImportResult(BaseModel):
    total:int
    valid:int
    invalid:int
    imported:int=0
    skipped:int=0
    rows:list[InventoryImportRow]

class StockItemCreate(BaseModel):
    item_name:str=Field(min_length=2,max_length=180)
    category:str=Field(default="Other",min_length=2,max_length=120)
    category_id:int|None=None
    item_type:str|None=Field(default=None,max_length=120)
    specifications:str|None=None
    quantity_available:int=Field(default=0,ge=0,le=1_000_000)
    low_stock_threshold:int=Field(default=5,ge=0,le=1_000_000)
    unit:str=Field(default="piece",min_length=1,max_length=50)
    donor:str|None=Field(default=None,max_length=120)
    project_code:str|None=Field(default=None,max_length=120)
    unit_price:float=Field(default=0,ge=0)
    currency:str=Field(default="AFN",min_length=2,max_length=20)
    expiration_date:date|None=None
    location:str=Field(min_length=1,max_length=180)
    responsible_person_id:int|None=None
    notes:str|None=None
class StockItemUpdate(BaseModel):
    item_name:str|None=None; category:str|None=None; category_id:int|None=None; item_type:str|None=None; specifications:str|None=None
    quantity_available:int|None=Field(default=None,ge=0,le=1_000_000)
    low_stock_threshold:int|None=Field(default=None,ge=0,le=1_000_000)
    unit:str|None=None; donor:str|None=None; project_code:str|None=None; unit_price:float|None=None
    currency:str|None=None; expiration_date:date|None=None; location:str|None=None; responsible_person_id:int|None=None
    notes:str|None=None; is_active:bool|None=None
class StockItemRead(StockItemCreate):
    id:int; status:str; is_active:bool; picture_url:str|None=None; responsible_person_name:str|None=None; category_name:str
    created_at:datetime; updated_at:datetime
    model_config=ConfigDict(from_attributes=True)
class StockRequestCreate(BaseModel):
    item_id:int
    requested_quantity:int=Field(ge=1,le=100_000)
    location:str=Field(min_length=1,max_length=180)
    reason:str=Field(min_length=3,max_length=5000)
class StockRequestDecision(BaseModel):
    status:Literal["Approved","Rejected","Ready for Pickup","Delivered","Cancelled"]
    notes:str|None=Field(default=None,max_length=5000)
class StockRequestRead(BaseModel):
    id:int; request_number:str; requested_by_id:int; department:str|None; location:str
    item_id:int; requested_quantity:int; reason:str; status:str; approved_by_id:int|None
    delivered_by_id:int|None; notes:str|None; request_date:datetime; decision_date:datetime|None
    delivery_date:datetime|None; updated_at:datetime
    requested_by_name:str; item_name:str; approved_by_name:str|None=None; delivered_by_name:str|None=None
    model_config=ConfigDict(from_attributes=True)

