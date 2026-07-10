import ipaddress
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db
from app.lan_schemas import (
    CallCreate, ConversationCreate, ConversationUpdate, LanSettingsUpdate,
    MeetingCreate, MemberAdd, MessageCreate, MessageUpdate,
)
from app.models import (
    AuditLog, LanAttachment, LanCallParticipant, LanCallSession, LanConversation,
    LanConversationMember, LanMeeting, LanMeetingParticipant, LanMessage,
    LanMessengerSettings, User, UserRole,
)
from app.modules import permissions_for_role
from app.pagination import page_result
from app.security import get_current_user, require_permission
from app.services.attachment_service import safe_display_name


def require_lan_available(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    row = lan_settings(db)
    detected, _ = network_context(request, row)
    if "can_manage_lan_messenger_settings" in permissions_for_role(user.role):
        return user
    if not row.enabled:
        raise HTTPException(503, "LAN Messenger is disabled")
    if detected == "public" and not row.allow_external_access:
        raise HTTPException(403, "External LAN Messenger access is disabled")
    return user


router = APIRouter(
    prefix="/lan-messenger", tags=["LAN Messenger"],
    dependencies=[
        Depends(require_permission("can_access_lan_messenger")),
        Depends(require_lan_available),
    ],
)
ADMIN_ROLES = {UserRole.ADMIN, UserRole.SUPER_ADMIN}
ALLOWED_EXTENSIONS = {".pdf",".doc",".docx",".xls",".xlsx",".csv",".txt",".png",".jpg",".jpeg",".webp"}
ALLOWED_MIME_TYPES = {
    "application/pdf","application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv","text/plain","image/png","image/jpeg","image/webp",
}


def lan_settings(db: Session) -> LanMessengerSettings:
    row = db.get(LanMessengerSettings, 1)
    if not row:
        row = LanMessengerSettings(
            id=1,
            internal_lan_base_url=app_settings.lan_messenger_internal_base_url or None,
            public_base_url=app_settings.lan_messenger_public_base_url or app_settings.public_app_url,
            lan_cidrs=app_settings.lan_messenger_lan_cidr_list,
        )
        db.add(row); db.flush()
    return row


def network_context(request: Request, row: LanMessengerSettings) -> tuple[str, str | None]:
    raw_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "")
    try:
        address = ipaddress.ip_address(raw_ip)
        on_lan = address.is_private or any(address in ipaddress.ip_network(cidr) for cidr in row.lan_cidrs)
    except ValueError:
        on_lan = False
    if on_lan:
        preferred = (
            row.internal_lan_base_url
            if row.prefer_lan_for_private_ips and row.internal_lan_base_url
            else row.public_base_url or row.internal_lan_base_url
        )
        return "lan", preferred
    return "public", row.public_base_url or row.internal_lan_base_url


def member(db: Session, conversation_id: int, user_id: int) -> LanConversationMember | None:
    return db.query(LanConversationMember).filter_by(conversation_id=conversation_id, user_id=user_id).first()


def require_member(db: Session, conversation_id: int, user: User) -> tuple[LanConversation, LanConversationMember | None]:
    conversation = db.get(LanConversation, conversation_id)
    if not conversation or not conversation.is_active:
        raise HTTPException(404, "Conversation not found")
    membership = member(db, conversation_id, user.id)
    if not membership and user.role not in ADMIN_ROLES:
        raise HTTPException(403, "You are not a member of this conversation")
    return conversation, membership


def conversation_payload(row: LanConversation) -> dict:
    return {
        "id":row.id,"type":row.type,"name":row.name,"description":row.description,
        "is_private":row.is_private,"is_active":row.is_active,
        "created_by_id":row.created_by_id,"created_at":row.created_at,"updated_at":row.updated_at,
        "members":[{
            "user_id":entry.user_id,"full_name":entry.user.full_name,"email":entry.user.email,
            "profile_picture_url":entry.user.profile_picture_url,
            "role":entry.role,"joined_at":entry.joined_at,
        } for entry in row.members],
    }


def message_payload(row: LanMessage) -> dict:
    return {
        "id":row.id,"conversation_id":row.conversation_id,"sender_id":row.sender_id,
        "sender_name":row.sender.full_name,
        "sender_profile_picture_url":row.sender.profile_picture_url,
        "content":"" if row.is_deleted else row.content,
        "message_type":row.message_type,"is_edited":row.is_edited,"is_deleted":row.is_deleted,
        "created_at":row.created_at,"updated_at":row.updated_at,
        "attachments":[{
            "id":item.id,"original_filename":item.original_filename,"mime_type":item.mime_type,
            "file_size":item.file_size,"created_at":item.created_at,
        } for item in row.attachments],
    }


def meeting_access(db: Session, meeting: LanMeeting, user: User) -> bool:
    if user.role in ADMIN_ROLES or meeting.scheduled_by_id == user.id:
        return True
    if db.query(LanMeetingParticipant.id).filter_by(meeting_id=meeting.id,user_id=user.id).first():
        return True
    return bool(meeting.conversation_id and member(db, meeting.conversation_id, user.id))


def meeting_payload(row: LanMeeting) -> dict:
    return {
        "id":row.id,"title":row.title,"description":row.description,
        "meeting_type":row.meeting_type,"conversation_id":row.conversation_id,
        "scheduled_by_id":row.scheduled_by_id,"start_time":row.start_time,"end_time":row.end_time,
        "status":row.status,"participant_ids":[item.user_id for item in row.participants],
        "created_at":row.created_at,
    }


def call_payload(row: LanCallSession) -> dict:
    return {
        "id":row.id,"conversation_id":row.conversation_id,"meeting_id":row.meeting_id,
        "started_by_id":row.started_by_id,"call_type":row.call_type,"call_scope":row.call_scope,
        "status":row.status,"started_at":row.started_at,"ended_at":row.ended_at,
        "participants":[{
            "user_id":item.user_id,"full_name":item.user.full_name,"status":item.status,
            "profile_picture_url":item.user.profile_picture_url,
            "joined_at":item.joined_at,"left_at":item.left_at,
            "is_muted":item.is_muted,"is_video_enabled":item.is_video_enabled,
        } for item in row.participants],
    }


@router.get("/settings")
def get_settings(request: Request, db: Session=Depends(get_db)):
    row=lan_settings(db); detected,preferred=network_context(request,row); db.commit()
    return {**{column.name:getattr(row,column.name) for column in row.__table__.columns if column.name not in {"updated_by_id","created_at"}}, "preferred_base_url":preferred,"detected_network":detected}


@router.put("/settings")
def update_settings(data: LanSettingsUpdate, request: Request, db: Session=Depends(get_db), actor: User=Depends(require_permission("can_manage_lan_messenger_settings"))):
    for cidr in data.lan_cidrs:
        try: ipaddress.ip_network(cidr)
        except ValueError: raise HTTPException(422,f"Invalid LAN CIDR: {cidr}")
    row=lan_settings(db)
    for key,value in data.model_dump().items(): setattr(row,key,value)
    row.updated_by_id=actor.id
    db.add(AuditLog(actor_id=actor.id,action="LAN Messenger settings changed",details={"lan_cidrs":data.lan_cidrs}))
    db.commit();db.refresh(row)
    detected,preferred=network_context(request,row)
    return {**{column.name:getattr(row,column.name) for column in row.__table__.columns if column.name not in {"updated_by_id","created_at"}}, "preferred_base_url":preferred,"detected_network":detected}


@router.get("/users")
def search_users(q:str|None=Query(None,max_length=120),db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    query=db.query(User).filter(User.is_active.is_(True),User.id!=actor.id)
    if q:
        term=f"%{q.strip()}%";query=query.filter(or_(User.full_name.ilike(term),User.email.ilike(term),User.department.ilike(term)))
    return [{
        "id":u.id,"full_name":u.full_name,"email":u.email,
        "department":u.department,"profile_picture_url":u.profile_picture_url,
    } for u in query.order_by(User.full_name).limit(30)]


@router.get("/conversations")
def list_conversations(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    query=db.query(LanConversation).join(LanConversationMember).filter(LanConversationMember.user_id==user.id,LanConversation.is_active.is_(True)).order_by(LanConversation.updated_at.desc())
    return [conversation_payload(row) for row in query.all()]


@router.post("/conversations",status_code=201)
def create_conversation(data:ConversationCreate,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    perms=permissions_for_role(actor.role); cfg=lan_settings(db)
    needed={"direct":"can_send_lan_messages","group":"can_create_lan_groups","channel":"can_create_lan_channels"}[data.type]
    if needed not in perms: raise HTTPException(403,"You cannot create this conversation type")
    if not getattr(cfg,{"direct":"allow_direct_messages","group":"allow_groups","channel":"allow_channels"}[data.type]):
        raise HTTPException(409,"This conversation type is disabled")
    user_ids=list(dict.fromkeys([actor.id,*data.member_ids]))
    users=db.query(User).filter(User.id.in_(user_ids),User.is_active.is_(True)).all()
    if len(users)!=len(user_ids): raise HTTPException(422,"One or more members were not found")
    if data.type=="direct":
        other=data.member_ids[0]
        existing=db.query(LanConversation).join(LanConversationMember).filter(LanConversation.type=="direct",LanConversationMember.user_id==actor.id).all()
        for row in existing:
            if {m.user_id for m in row.members}=={actor.id,other}: return conversation_payload(row)
    row=LanConversation(type=data.type,name=data.name,description=data.description,is_private=data.is_private,created_by_id=actor.id)
    db.add(row);db.flush()
    for uid in user_ids: db.add(LanConversationMember(conversation_id=row.id,user_id=uid,role="owner" if uid==actor.id else "member"))
    db.add(AuditLog(actor_id=actor.id,action=f"LAN {data.type} created",details={"conversation_id":row.id}))
    db.commit();db.refresh(row);return conversation_payload(row)


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    row,_=require_member(db,conversation_id,user);return conversation_payload(row)


@router.put("/conversations/{conversation_id}")
def update_conversation(conversation_id:int,data:ConversationUpdate,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    row,membership=require_member(db,conversation_id,actor)
    if actor.role not in ADMIN_ROLES and (not membership or membership.role not in {"owner","admin"}): raise HTTPException(403,"Conversation admin access required")
    for key,value in data.model_dump(exclude_unset=True).items():setattr(row,key,value)
    db.commit();db.refresh(row);return conversation_payload(row)


@router.patch("/conversations/{conversation_id}/archive")
def archive_conversation(conversation_id:int,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    row,membership=require_member(db,conversation_id,actor)
    if actor.role not in ADMIN_ROLES and (not membership or membership.role!="owner"): raise HTTPException(403,"Conversation owner access required")
    row.is_active=False;db.add(AuditLog(actor_id=actor.id,action="LAN conversation archived",details={"conversation_id":row.id}));db.commit()
    return {"status":"archived"}


@router.get("/conversations/{conversation_id}/members")
def list_members(conversation_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    row,_=require_member(db,conversation_id,user);return conversation_payload(row)["members"]


@router.post("/conversations/{conversation_id}/members",status_code=201)
def add_member(conversation_id:int,data:MemberAdd,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    row,membership=require_member(db,conversation_id,actor)
    if row.type=="direct":raise HTTPException(409,"Direct conversation membership cannot change")
    if actor.role not in ADMIN_ROLES and (not membership or membership.role not in {"owner","admin"}):raise HTTPException(403,"Conversation admin access required")
    if member(db,row.id,data.user_id):raise HTTPException(409,"User is already a member")
    if not db.get(User,data.user_id):raise HTTPException(404,"User not found")
    db.add(LanConversationMember(conversation_id=row.id,user_id=data.user_id,role=data.role))
    db.add(AuditLog(actor_id=actor.id,action="LAN group member added",details={"conversation_id":row.id,"user_id":data.user_id}))
    db.commit();return {"status":"added"}


@router.delete("/conversations/{conversation_id}/members/{user_id}",status_code=204)
def remove_member(conversation_id:int,user_id:int,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    row,membership=require_member(db,conversation_id,actor)
    if actor.role not in ADMIN_ROLES and (not membership or membership.role not in {"owner","admin"}):raise HTTPException(403,"Conversation admin access required")
    target=member(db,row.id,user_id)
    if not target:raise HTTPException(404,"Member not found")
    db.delete(target);db.add(AuditLog(actor_id=actor.id,action="LAN group member removed",details={"conversation_id":row.id,"user_id":user_id}));db.commit()


@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id:int,page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=100),db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    require_member(db,conversation_id,user)
    result=page_result(db.query(LanMessage).filter_by(conversation_id=conversation_id).order_by(LanMessage.created_at.desc()),page,page_size)
    result["items"]=[message_payload(row) for row in reversed(result["items"])]
    return result


@router.post("/conversations/{conversation_id}/messages",status_code=201)
def send_message(conversation_id:int,data:MessageCreate,db:Session=Depends(get_db),actor:User=Depends(require_permission("can_send_lan_messages"))):
    row,_=require_member(db,conversation_id,actor)
    message=LanMessage(conversation_id=row.id,sender_id=actor.id,content=data.content,parent_message_id=data.parent_message_id)
    row.updated_at=datetime.now(timezone.utc);db.add(message);db.commit();db.refresh(message);return message_payload(message)


@router.put("/messages/{message_id}")
def edit_message(message_id:int,data:MessageUpdate,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    row=db.get(LanMessage,message_id)
    if not row:raise HTTPException(404,"Message not found")
    require_member(db,row.conversation_id,actor)
    if row.sender_id!=actor.id:raise HTTPException(403,"Only the sender can edit this message")
    row.content=data.content;row.is_edited=True;db.commit();db.refresh(row);return message_payload(row)


@router.delete("/messages/{message_id}",status_code=204)
def delete_message(message_id:int,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    row=db.get(LanMessage,message_id)
    if not row:raise HTTPException(404,"Message not found")
    require_member(db,row.conversation_id,actor)
    if row.sender_id!=actor.id and actor.role not in ADMIN_ROLES:raise HTTPException(403,"Cannot delete this message")
    row.is_deleted=True;row.content="";db.commit()


@router.post("/messages/{message_id}/attachments",status_code=201)
async def upload_attachment(message_id:int,file:UploadFile=File(...),db:Session=Depends(get_db),actor:User=Depends(require_permission("can_upload_lan_attachments"))):
    message=db.get(LanMessage,message_id)
    if not message:raise HTTPException(404,"Message not found")
    require_member(db,message.conversation_id,actor);cfg=lan_settings(db)
    if not cfg.allow_file_uploads:raise HTTPException(409,"File uploads are disabled")
    original=safe_display_name(file.filename);ext=Path(original).suffix.lower();mime=(file.content_type or "").lower()
    if ext not in ALLOWED_EXTENSIONS or mime not in ALLOWED_MIME_TYPES:raise HTTPException(415,"Unsupported file type")
    limit=cfg.max_file_size_mb*1_048_576;content=await file.read(limit+1);await file.close()
    if not content:raise HTTPException(422,"The uploaded file is empty")
    if len(content)>limit:raise HTTPException(413,f"Files must be smaller than {cfg.max_file_size_mb} MB")
    if ext in {".png"} and not content.startswith(b"\x89PNG"):raise HTTPException(415,"File content does not match PNG")
    if ext in {".jpg",".jpeg"} and not content.startswith(b"\xff\xd8\xff"):raise HTTPException(415,"File content does not match JPEG")
    if ext==".pdf" and not content.startswith(b"%PDF-"):raise HTTPException(415,"File content does not match PDF")
    directory=(app_settings.upload_directory/"lan-messenger").resolve();directory.mkdir(parents=True,exist_ok=True)
    stored=f"{uuid4().hex}{ext}";path=(directory/stored).resolve()
    if directory not in path.parents:raise HTTPException(400,"Invalid upload path")
    path.write_bytes(content)
    row=LanAttachment(message_id=message.id,uploaded_by_id=actor.id,original_filename=original,stored_filename=stored,mime_type=mime,file_size=len(content))
    message.message_type="attachment";db.add(row);db.flush()
    db.add(AuditLog(actor_id=actor.id,action="LAN attachment uploaded",details={"attachment_id":row.id,"conversation_id":message.conversation_id}))
    db.commit();db.refresh(row)
    return {"id":row.id,"original_filename":row.original_filename,"mime_type":row.mime_type,"file_size":row.file_size,"created_at":row.created_at}


@router.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    row=db.get(LanAttachment,attachment_id)
    if not row:raise HTTPException(404,"Attachment not found")
    require_member(db,row.message.conversation_id,user)
    directory=(app_settings.upload_directory/"lan-messenger").resolve();path=(directory/Path(row.stored_filename).name).resolve()
    if directory not in path.parents or not path.is_file():raise HTTPException(404,"Attachment file not found")
    return FileResponse(path,media_type=row.mime_type,filename=row.original_filename,headers={"X-Content-Type-Options":"nosniff"})


@router.get("/meetings")
def list_meetings(status:str|None=None,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    rows=db.query(LanMeeting).order_by(LanMeeting.start_time.desc()).all()
    return [meeting_payload(row) for row in rows if (not status or row.status==status) and meeting_access(db,row,user)]


@router.post("/meetings",status_code=201)
def create_meeting(data:MeetingCreate,db:Session=Depends(get_db),actor:User=Depends(require_permission("can_schedule_lan_meetings"))):
    cfg=lan_settings(db)
    if not cfg.allow_meetings:raise HTTPException(409,"Meetings are disabled")
    if data.conversation_id:require_member(db,data.conversation_id,actor)
    participant_ids=set(data.participant_ids)
    if data.conversation_id:participant_ids.update(item.user_id for item in db.query(LanConversationMember).filter_by(conversation_id=data.conversation_id))
    participant_ids.add(actor.id)
    row=LanMeeting(**data.model_dump(exclude={"participant_ids"}),scheduled_by_id=actor.id)
    db.add(row);db.flush()
    for uid in participant_ids:db.add(LanMeetingParticipant(meeting_id=row.id,user_id=uid,status="accepted" if uid==actor.id else "invited"))
    db.add(AuditLog(actor_id=actor.id,action="LAN meeting scheduled",details={"meeting_id":row.id}))
    db.commit();db.refresh(row);return meeting_payload(row)


@router.get("/meetings/{meeting_id}")
def get_meeting(meeting_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    row=db.get(LanMeeting,meeting_id)
    if not row:raise HTTPException(404,"Meeting not found")
    if not meeting_access(db,row,user):raise HTTPException(403,"Meeting access denied")
    return meeting_payload(row)


@router.put("/meetings/{meeting_id}")
def update_meeting(meeting_id:int,data:MeetingCreate,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    row=db.get(LanMeeting,meeting_id)
    if not row:raise HTTPException(404,"Meeting not found")
    if actor.role not in ADMIN_ROLES and row.scheduled_by_id!=actor.id:raise HTTPException(403,"Meeting owner access required")
    for key,value in data.model_dump(exclude={"participant_ids"}).items():setattr(row,key,value)
    db.add(AuditLog(actor_id=actor.id,action="LAN meeting updated",details={"meeting_id":row.id}));db.commit();db.refresh(row);return meeting_payload(row)


@router.patch("/meetings/{meeting_id}/cancel")
def cancel_meeting(meeting_id:int,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    row=db.get(LanMeeting,meeting_id)
    if not row:raise HTTPException(404,"Meeting not found")
    if actor.role not in ADMIN_ROLES and row.scheduled_by_id!=actor.id:raise HTTPException(403,"Meeting owner access required")
    row.status="cancelled";db.add(AuditLog(actor_id=actor.id,action="LAN meeting cancelled",details={"meeting_id":row.id}));db.commit();return {"status":"cancelled"}


@router.post("/meetings/{meeting_id}/join")
def join_meeting(meeting_id:int,db:Session=Depends(get_db),user:User=Depends(require_permission("can_join_lan_meetings"))):
    row=db.get(LanMeeting,meeting_id)
    if not row or not meeting_access(db,row,user):raise HTTPException(403,"Meeting access denied")
    participant=db.query(LanMeetingParticipant).filter_by(meeting_id=meeting_id,user_id=user.id).first()
    if not participant:participant=LanMeetingParticipant(meeting_id=meeting_id,user_id=user.id)
    participant.status="accepted";participant.joined_at=datetime.now(timezone.utc);participant.left_at=None;db.add(participant);db.commit()
    return {"status":"joined"}


@router.post("/meetings/{meeting_id}/leave")
def leave_meeting(meeting_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    participant=db.query(LanMeetingParticipant).filter_by(meeting_id=meeting_id,user_id=user.id).first()
    if not participant:raise HTTPException(404,"Meeting participant not found")
    participant.left_at=datetime.now(timezone.utc);db.commit();return {"status":"left"}


def start_call(db:Session,actor:User,call_type:str,conversation:LanConversation|None=None,meeting:LanMeeting|None=None):
    cfg=lan_settings(db);scope="meeting" if meeting else conversation.type
    if call_type=="voice" and not cfg.allow_voice_calls:raise HTTPException(409,"Voice calls are disabled")
    if call_type=="video" and not cfg.allow_video_calls:raise HTTPException(409,"Video calls are disabled")
    if scope in {"group","channel"} and call_type=="voice" and not cfg.allow_group_voice_calls:raise HTTPException(409,"Group voice calls are disabled")
    if scope in {"group","channel"} and call_type=="video" and not cfg.allow_group_video_calls:raise HTTPException(409,"Group video calls are disabled")
    if meeting and not cfg.allow_meeting_calls:raise HTTPException(409,"Meeting calls are disabled")
    ids={item.user_id for item in (meeting.participants if meeting else conversation.members)}
    row=LanCallSession(conversation_id=conversation.id if conversation else None,meeting_id=meeting.id if meeting else None,started_by_id=actor.id,call_type=call_type,call_scope=scope,status="active")
    db.add(row);db.flush()
    for uid in ids:db.add(LanCallParticipant(call_session_id=row.id,user_id=uid,status="joined" if uid==actor.id else "ringing",joined_at=datetime.now(timezone.utc) if uid==actor.id else None,is_video_enabled=call_type=="video" and uid==actor.id))
    if conversation:db.add(LanMessage(conversation_id=conversation.id,sender_id=actor.id,content=f"{actor.full_name} started a {call_type} call",message_type="call"))
    db.add(AuditLog(actor_id=actor.id,action="LAN call started",details={"call_id":row.id,"scope":scope,"type":call_type}))
    db.commit();db.refresh(row);return call_payload(row)


@router.post("/conversations/{conversation_id}/calls",status_code=201)
def conversation_call(conversation_id:int,data:CallCreate,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    row,_=require_member(db,conversation_id,actor)
    permission="can_start_lan_video_call" if data.call_type=="video" else "can_start_lan_voice_call"
    group_permission="can_start_lan_group_video_call" if data.call_type=="video" else "can_start_lan_group_voice_call"
    perms=permissions_for_role(actor.role)
    if permission not in perms or (row.type!="direct" and group_permission not in perms):raise HTTPException(403,"Call permission denied")
    return start_call(db,actor,data.call_type,conversation=row)


@router.post("/meetings/{meeting_id}/calls",status_code=201)
def meeting_call(meeting_id:int,data:CallCreate,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    row=db.get(LanMeeting,meeting_id)
    if not row or not meeting_access(db,row,actor):raise HTTPException(403,"Meeting access denied")
    return start_call(db,actor,data.call_type,meeting=row)


@router.get("/calls/active")
def active_calls(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    rows=db.query(LanCallSession).join(LanCallParticipant).filter(LanCallParticipant.user_id==user.id,LanCallSession.status=="active").all()
    return [call_payload(row) for row in rows]


@router.get("/calls/{call_id}")
def get_call(call_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    row=db.get(LanCallSession,call_id)
    if not row or not any(item.user_id==user.id for item in row.participants) and user.role not in ADMIN_ROLES:raise HTTPException(403,"Call access denied")
    return call_payload(row)


@router.post("/calls/{call_id}/join")
def join_call(call_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    row=db.get(LanCallSession,call_id);participant=db.query(LanCallParticipant).filter_by(call_session_id=call_id,user_id=user.id).first()
    if not row or not participant:raise HTTPException(403,"Call access denied")
    if row.status!="active":raise HTTPException(409,"Call has ended")
    participant.status="joined";participant.joined_at=datetime.now(timezone.utc);participant.left_at=None;db.commit();return call_payload(row)


@router.post("/calls/{call_id}/leave")
def leave_call(call_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    participant=db.query(LanCallParticipant).filter_by(call_session_id=call_id,user_id=user.id).first()
    if not participant:raise HTTPException(403,"Call access denied")
    participant.status="left";participant.left_at=datetime.now(timezone.utc);db.commit();return {"status":"left"}


@router.put("/calls/{call_id}/end")
def end_call(call_id:int,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    row=db.get(LanCallSession,call_id)
    if not row:raise HTTPException(404,"Call not found")
    if row.started_by_id!=actor.id and actor.role not in ADMIN_ROLES:raise HTTPException(403,"Only the call starter can end it")
    row.status="ended";row.ended_at=datetime.now(timezone.utc)
    for item in row.participants:
        if item.status in {"joined","ringing"}:item.status="left";item.left_at=row.ended_at
    db.add(AuditLog(actor_id=actor.id,action="LAN call ended",details={"call_id":row.id}));db.commit();db.refresh(row);return call_payload(row)
