from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RecipientInput(BaseModel):
    user_id: int
    role_name: str | None = Field(default=None, max_length=120)
    routing_order: int = Field(ge=1, le=100)
    signature_page: int | None = Field(default=None, ge=-1, le=1000)
    signature_x: float | None = Field(default=None, ge=0, le=.95)
    signature_y: float | None = Field(default=None, ge=0, le=.95)
    signature_width: float | None = Field(default=None, ge=.08, le=.7)
    signature_height: float | None = Field(default=None, ge=.06, le=.5)


class EnvelopeCreate(BaseModel):
    document_type: Literal[
        "purchase_request", "purchase_order", "asset_form",
        "stock_document", "contract", "general_document",
    ] = "general_document"
    document_reference_id: str | None = Field(default=None, max_length=120)
    title: str = Field(min_length=2, max_length=220)
    subject: str | None = Field(default=None, max_length=255)
    message: str | None = Field(default=None, max_length=4000)
    routing_mode: Literal["sequential"] = "sequential"
    recipients: list[RecipientInput] = Field(min_length=1, max_length=25)


class RecipientRead(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: EmailStr
    role_name: str | None
    routing_order: int
    signature_page: int
    signature_x: float
    signature_y: float
    signature_width: float
    signature_height: float
    status: str
    verification_number: str | None
    signed_at: datetime | None
    viewed_at: datetime | None
    comment: str | None
    model_config = ConfigDict(from_attributes=True)


class EnvelopeRead(BaseModel):
    id: int
    envelope_id: str
    document_type: str
    document_reference_id: str | None
    title: str
    subject: str | None
    message: str | None
    status: str
    routing_mode: str
    original_pdf_hash: str
    current_document_hash: str
    final_signed_pdf_hash: str | None
    created_by_id: int
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    recipients: list[RecipientRead] = []
    model_config = ConfigDict(from_attributes=True)


class EnvelopePage(BaseModel):
    items: list[EnvelopeRead]
    total: int
    page: int
    page_size: int
    pages: int


class ReviewRead(BaseModel):
    envelope: EnvelopeRead
    recipient: RecipientRead
    can_act: bool
    document_url: str


class SignAction(BaseModel):
    confirmed_review: bool
    typed_name: str | None = Field(default=None, max_length=120)


class CommentAction(BaseModel):
    comment: str = Field(min_length=2, max_length=2000)


class SignSettingsUpdate(BaseModel):
    is_enabled: bool = True
    require_signature_image: bool = False
    default_token_expiry_hours: int = Field(default=72, ge=1, le=720)
    allow_public_verification: bool = False
    default_routing_mode: Literal["sequential"] = "sequential"
    email_notification_enabled: bool = True
    signature_stamp_position: Literal["signature_page", "bottom_page"] = "signature_page"
    max_signature_image_size: int = Field(default=3_145_728, ge=102_400, le=5_242_880)
    allowed_signature_image_types: list[str] = ["image/png", "image/jpeg", "image/webp"]


class SignSettingsRead(SignSettingsUpdate):
    id: int
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
