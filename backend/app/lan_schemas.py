from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ConversationType = Literal["direct", "group", "channel"]


class ConversationCreate(BaseModel):
    type: ConversationType
    name: str | None = Field(default=None, max_length=180)
    description: str | None = None
    is_private: bool = True
    member_ids: list[int] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def validate_members(self):
        if self.type == "direct" and len(set(self.member_ids)) != 1:
            raise ValueError("Direct conversations require exactly one other user")
        if self.type != "direct" and not self.name:
            raise ValueError("Groups and channels require a name")
        return self


class ConversationUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=180)
    description: str | None = None
    is_private: bool | None = None


class MemberRead(BaseModel):
    user_id: int
    full_name: str
    email: str
    profile_picture_url: str | None = None
    role: str
    joined_at: datetime


class ConversationRead(BaseModel):
    id: int
    type: str
    name: str | None
    description: str | None
    is_private: bool
    is_active: bool
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    members: list[MemberRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class MemberAdd(BaseModel):
    user_id: int
    role: Literal["admin", "member"] = "member"


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)
    parent_message_id: int | None = None


class MessageUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)


class AttachmentRead(BaseModel):
    id: int
    original_filename: str
    mime_type: str
    file_size: int
    created_at: datetime


class MessageRead(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    sender_name: str
    sender_profile_picture_url: str | None = None
    content: str
    message_type: str
    is_edited: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    attachments: list[AttachmentRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class MeetingCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    meeting_type: Literal["voice", "video", "in_person", "hybrid"]
    conversation_id: int | None = None
    participant_ids: list[int] = Field(default_factory=list, max_length=200)
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def valid_time(self):
        if self.end_time <= self.start_time:
            raise ValueError("Meeting end time must be after start time")
        return self


class MeetingRead(BaseModel):
    id: int
    title: str
    description: str | None
    meeting_type: str
    conversation_id: int | None
    scheduled_by_id: int
    start_time: datetime
    end_time: datetime
    status: str
    participant_ids: list[int] = Field(default_factory=list)
    created_at: datetime


class CallCreate(BaseModel):
    call_type: Literal["voice", "video"]


class CallRead(BaseModel):
    id: int
    conversation_id: int | None
    meeting_id: int | None
    started_by_id: int
    call_type: str
    call_scope: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    participants: list[dict] = Field(default_factory=list)


class LanSettingsUpdate(BaseModel):
    enabled: bool = True
    internal_lan_base_url: str | None = Field(default=None, max_length=500)
    public_base_url: str | None = Field(default=None, max_length=500)
    lan_cidrs: list[str] = Field(default_factory=list, max_length=50)
    prefer_lan_for_private_ips: bool = True
    allow_external_access: bool = True
    allow_direct_messages: bool = True
    allow_groups: bool = True
    allow_channels: bool = True
    allow_meetings: bool = True
    allow_file_uploads: bool = True
    allow_voice_calls: bool = True
    allow_video_calls: bool = True
    allow_group_voice_calls: bool = True
    allow_group_video_calls: bool = True
    allow_meeting_calls: bool = True
    max_file_size_mb: int = Field(default=10, ge=1, le=100)


class LanSettingsRead(LanSettingsUpdate):
    id: int
    preferred_base_url: str | None = None
    detected_network: str = "unknown"
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
