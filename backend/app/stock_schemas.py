from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

class StockCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    icon: str = Field(default="Package", max_length=80)
    display_order: int = Field(default=0, ge=0, le=10_000)
    is_active: bool = True


class StockCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    icon: str | None = Field(default=None, max_length=80)
    display_order: int | None = Field(default=None, ge=0, le=10_000)
    is_active: bool | None = None


class StockCategoryRead(StockCategoryCreate):
    id: int
    item_count: int = 0
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StockCardCreate(BaseModel):
    base: str = Field(pattern=r"^[A-Za-z]{3}$")
    storage_location: str = Field(pattern=r"^[A-Za-z]{2}[0-9]$")
    sequence_number: str = Field(pattern=r"^[0-9]{3}$")
    donor: str | None = Field(default=None, max_length=120)
    project_code: str | None = Field(default=None, max_length=120)
    stock_item_id: int
    specifications: str | None = None
    unit: str = Field(min_length=1, max_length=50)
    expiration_date: date | None = None
    unit_price: float = Field(default=0, ge=0)
    currency: str = Field(default="AFN", min_length=2, max_length=20)
    comments: str | None = None
    opening_quantity: float = Field(default=0, ge=0)
    minimum_quantity: float = Field(default=0, ge=0)


class StockCardUpdate(BaseModel):
    donor: str | None = None
    project_code: str | None = None
    specifications: str | None = None
    unit: str | None = None
    expiration_date: date | None = None
    unit_price: float | None = Field(default=None, ge=0)
    currency: str | None = None
    comments: str | None = None
    opening_quantity: float | None = Field(default=None, ge=0)
    minimum_quantity: float | None = Field(default=None, ge=0)
    is_active: bool | None = None


class StockCardRead(StockCardCreate):
    id: int
    stock_card_number: str
    item_name: str
    is_active: bool
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StockMovementCreate(BaseModel):
    stock_item_id: int
    stock_card_id: int | None = None
    movement_date: date
    movement_type: Literal["IN", "OUT", "TRANSFER", "ADJUSTMENT", "DAMAGED", "LOST", "BROKEN"]
    quantity_in: float = Field(default=0, ge=0)
    quantity_out: float = Field(default=0, ge=0)
    po_number: str | None = None
    waybill_number: str | None = None
    goods_received_note_no: str | None = None
    stock_transfer_no: str | None = None
    destination: str | None = None
    remarks: str | None = None
    comments: str | None = None
    signature_name: str | None = None
    mission: str = "DEMO MISSION"
    base: str = "COORDINATION"


class StockMovementRead(StockMovementCreate):
    id: int
    month_number: int
    year: int
    quantity_change: int
    performed_by_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ImportRow(BaseModel):
    row: int
    status: str
    detail: str | None = None
    data: dict = Field(default_factory=dict)


class ImportPreview(BaseModel):
    valid: int
    invalid: int
    created: int = 0
    rows: list[ImportRow]


class PhysicalCountCreate(BaseModel):
    stock_item_id: int
    stock_card_id: int | None = None
    count_date: date
    physical_quantity: float = Field(ge=0)
    notes: str | None = None


class DashboardCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str | None = None
    embed_url: str = Field(min_length=10, max_length=1200)
    provider: str = Field(default="Power BI", max_length=50)
    is_active: bool = True
    allowed_roles: list[str] = Field(default_factory=list)
    user_ids: list[int] = Field(default_factory=list)


class DashboardUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    embed_url: str | None = None
    provider: str | None = None
    is_active: bool | None = None
    allowed_roles: list[str] | None = None
    user_ids: list[int] | None = None


class DashboardRead(BaseModel):
    id: int
    title: str
    description: str | None
    embed_url: str
    provider: str
    is_active: bool
    allowed_roles: list[str]
    user_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
