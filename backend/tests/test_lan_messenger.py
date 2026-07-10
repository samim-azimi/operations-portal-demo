from datetime import datetime, timedelta, timezone

from app.models import User, UserRole
from app.security import hash_password
from conftest import TestingSession, login


def user_id(email):
    db=TestingSession();value=db.query(User).filter_by(email=email).one().id;db.close();return value


def create_group(client,headers,member_ids=None):
    response=client.post("/api/lan-messenger/conversations",json={
        "type":"group","name":"ICT Coordination","description":"LAN group",
        "is_private":True,"member_ids":member_ids or [],
    },headers=headers)
    assert response.status_code==201
    return response.json()


def settings_payload(client,headers):
    data=client.get("/api/lan-messenger/settings",headers=headers).json()
    for key in ("id","preferred_base_url","detected_network","updated_at"):
        data.pop(key,None)
    return data


def test_lan_module_access_and_direct_conversation(client,user_headers):
    modules=client.get("/api/modules",headers=user_headers).json()
    assert "lan_messenger" in [row["id"] for row in modules]
    support=user_id("support@test.com")
    created=client.post("/api/lan-messenger/conversations",json={
        "type":"direct","member_ids":[support],"is_private":True,
    },headers=user_headers)
    assert created.status_code==201
    assert created.json()["type"]=="direct"
    assert all("profile_picture_url" in member for member in created.json()["members"])
    db=TestingSession()
    db.add(User(full_name="Stock only",email="stockonly@test.com",password_hash=hash_password("stock123"),role=UserRole.STOCK_MANAGER))
    db.commit();db.close()
    headers={"Authorization":"Bearer "+login(client,"stockonly@test.com","stock123")}
    assert client.get("/api/lan-messenger/conversations",headers=headers).status_code==403
    assert "lan_messenger" not in [row["id"] for row in client.get("/api/modules",headers=headers).json()]


def test_group_membership_messages_and_attachment_security(client,user_headers,support_headers,manager_headers):
    support=user_id("support@test.com")
    group=create_group(client,user_headers,[support])
    assert client.get(f"/api/lan-messenger/conversations/{group['id']}",headers=manager_headers).status_code==403
    sent=client.post(f"/api/lan-messenger/conversations/{group['id']}/messages",json={"content":"LAN service is available"},headers=support_headers)
    assert sent.status_code==201
    assert "sender_profile_picture_url" in sent.json()
    invalid=client.post(f"/api/lan-messenger/messages/{sent.json()['id']}/attachments",files={"file":("malware.exe",b"MZ","application/octet-stream")},headers=support_headers)
    assert invalid.status_code==415
    valid=client.post(f"/api/lan-messenger/messages/{sent.json()['id']}/attachments",files={"file":("screen.png",b"\x89PNG\r\n\x1a\nimage","image/png")},headers=support_headers)
    assert valid.status_code==201
    attachment_id=valid.json()["id"]
    assert client.get(f"/api/lan-messenger/attachments/{attachment_id}/download",headers=support_headers).status_code==200
    assert client.get(f"/api/lan-messenger/attachments/{attachment_id}/download",headers=manager_headers).status_code==403


def test_meeting_validation_schedule_and_join(client,user_headers,support_headers):
    now=datetime.now(timezone.utc)+timedelta(hours=1)
    invalid=client.post("/api/lan-messenger/meetings",json={
        "title":"Invalid meeting","meeting_type":"video",
        "start_time":now.isoformat(),"end_time":(now-timedelta(minutes=5)).isoformat(),
    },headers=user_headers)
    assert invalid.status_code==422
    created=client.post("/api/lan-messenger/meetings",json={
        "title":"LAN planning","description":"Office coordination","meeting_type":"hybrid",
        "participant_ids":[user_id("support@test.com")],
        "start_time":now.isoformat(),"end_time":(now+timedelta(hours=1)).isoformat(),
    },headers=user_headers)
    assert created.status_code==201
    meeting_id=created.json()["id"]
    assert client.post(f"/api/lan-messenger/meetings/{meeting_id}/join",headers=support_headers).status_code==200


def test_group_call_lifecycle_toggle_and_settings(client,user_headers,support_headers,admin_headers):
    support=user_id("support@test.com")
    group=create_group(client,user_headers,[support])
    started=client.post(f"/api/lan-messenger/conversations/{group['id']}/calls",json={"call_type":"voice"},headers=user_headers)
    assert started.status_code==201
    call_id=started.json()["id"]
    assert client.post(f"/api/lan-messenger/calls/{call_id}/join",headers=support_headers).status_code==200
    assert client.post(f"/api/lan-messenger/calls/{call_id}/leave",headers=support_headers).status_code==200
    assert client.put(f"/api/lan-messenger/calls/{call_id}/end",headers=user_headers).json()["status"]=="ended"
    payload=settings_payload(client,admin_headers)
    payload.update({
        "internal_lan_base_url":"http://192.168.1.22:8000",
        "public_base_url":"https://demo.example.org",
        "lan_cidrs":["192.168.0.0/16"],"allow_group_voice_calls":False,
    })
    saved=client.put("/api/lan-messenger/settings",json=payload,headers=admin_headers)
    assert saved.status_code==200
    assert saved.json()["internal_lan_base_url"]=="http://192.168.1.22:8000"
    blocked=client.post(f"/api/lan-messenger/conversations/{group['id']}/calls",json={"call_type":"voice"},headers=user_headers)
    assert blocked.status_code==409
    assert client.put("/api/lan-messenger/settings",json=payload,headers=user_headers).status_code==403

