from app.services.ai_triage_service import AITriageService

TICKET={"full_name":"Demo User","email":"user@test.com","department":"Operations","location":"HQ","device_name":"LT-100","title":"Office internet is down","description":"The internet and Wi-Fi are not working for many users.","urgency":"High"}
def test_create_ticket_runs_validated_triage(client,user_headers):
    response=client.post("/api/tickets",json=TICKET,headers=user_headers)
    assert response.status_code==201
    data=response.json(); assert data["category"]=="Network"; assert data["priority"] in {"High","Critical"}; assert data["ai_analysis"]["provider"].startswith("rules"); assert data["human_approval_required"] is True

def test_fallback_ai_triage():
    class Ticket:
        title="Phishing message"; description="I clicked a suspicious phishing email"; urgency="High"; department="Finance"; location="HQ"; full_name="A User"
    result=AITriageService().fallback(Ticket())
    assert result.category=="Security"; assert result.priority=="High"; assert result.needs_human_approval; assert 0<=result.confidence_score<=1

def test_update_ticket_status(client,user_headers,support_headers):
    ticket=client.post("/api/tickets",json={**TICKET,"title":"Mouse is not working","description":"The USB mouse stopped working on my desk","urgency":"Low"},headers=user_headers).json()
    response=client.patch(f"/api/tickets/{ticket['id']}",json={"status":"In Progress"},headers=support_headers)
    assert response.status_code==200; assert response.json()["status"]=="In Progress"

def test_human_approval_blocks_resolution(client,user_headers,support_headers):
    ticket=client.post("/api/tickets",json=TICKET,headers=user_headers).json()
    blocked=client.patch(f"/api/tickets/{ticket['id']}",json={"status":"Resolved","resolution_notes":"Connectivity restored"},headers=support_headers)
    assert blocked.status_code==409
    approved=client.patch(f"/api/tickets/{ticket['id']}",json={"human_approved":True,"status":"Resolved","resolution_notes":"Network service restored"},headers=support_headers)
    assert approved.status_code==200; assert approved.json()["human_approved"] is True

def test_create_knowledge_base_article(client,admin_headers):
    payload={"title":"DNS troubleshooting","category":"Network","problem_description":"Names do not resolve","solution":"Verify DNS settings and flush the resolver cache.","tags":["dns","network"]}
    response=client.post("/api/knowledge-base",json=payload,headers=admin_headers)
    assert response.status_code==201; assert response.json()["title"]==payload["title"]

def test_dashboard_stats(client,user_headers,support_headers):
    client.post("/api/tickets",json=TICKET,headers=user_headers)
    response=client.get("/api/dashboard/stats",headers=support_headers)
    assert response.status_code==200; data=response.json(); assert data["total_tickets"]==1; assert data["critical_tickets"] in {0,1}; assert data["recent_tickets"]

def test_secure_attachment_upload_and_download(client,user_headers):
    ticket=client.post("/api/tickets",json=TICKET,headers=user_headers).json()
    content=b"\x89PNG\r\n\x1a\nsafe-test-image"
    uploaded=client.post(
        f"/api/tickets/{ticket['id']}/attachments",
        files={"file":("evidence.png",content,"image/png")},
        headers=user_headers,
    )
    assert uploaded.status_code==201
    attachment=uploaded.json()
    assert attachment["original_name"]=="evidence.png"
    downloaded=client.get(
        f"/api/tickets/{ticket['id']}/attachments/{attachment['id']}",
        headers=user_headers,
    )
    assert downloaded.status_code==200
    assert downloaded.content==content
    assert downloaded.headers["x-content-type-options"]=="nosniff"

def test_rejects_executable_attachment(client,user_headers):
    ticket=client.post("/api/tickets",json=TICKET,headers=user_headers).json()
    response=client.post(
        f"/api/tickets/{ticket['id']}/attachments",
        files={"file":("payload.exe",b"MZ-not-allowed","application/octet-stream")},
        headers=user_headers,
    )
    assert response.status_code==415

def test_security_headers(client):
    response=client.get("/health")
    assert response.headers["x-frame-options"]=="DENY"
    assert response.headers["x-content-type-options"]=="nosniff"
    assert "camera=()" in response.headers["permissions-policy"]

def test_admin_bulk_imports_edits_and_removes_users(client,admin_headers):
    csv_data=(
        "full_name,email,department,role\n"
        "Amina Rahimi,amina@example.com,Finance,user\n"
        "Farid Ahmadi,farid@example.com,ICT,support\n"
    )
    imported=client.post(
        "/api/users/bulk-import",
        files={"file":("employees.csv",csv_data,"text/csv")},
        headers=admin_headers,
    )
    assert imported.status_code==200
    assert imported.json()["created"]==2
    users=client.get("/api/users",headers=admin_headers).json()["items"]
    amina=next(user for user in users if user["email"]=="amina@example.com")
    edited=client.patch(
        f"/api/users/{amina['id']}",
        json={"department":"Operations"},
        headers=admin_headers,
    )
    assert edited.status_code==200
    assert edited.json()["department"]=="Operations"
    assert client.delete(f"/api/users/{amina['id']}",headers=admin_headers).status_code==204

def test_assign_and_collaborate_on_ticket(client,user_headers,support_headers):
    ticket=client.post("/api/tickets",json=TICKET,headers=user_headers).json()
    assignees=client.get("/api/users/assignees",headers=support_headers).json()
    support=next(person for person in assignees if person["role"]=="support")
    assigned=client.patch(
        f"/api/tickets/{ticket['id']}",
        json={"assigned_user_id":support["id"]},
        headers=support_headers,
    )
    assert assigned.status_code==200
    assert assigned.json()["assigned_user_name"]=="Support"
    sent=client.post(
        f"/api/tickets/{ticket['id']}/messages",
        json={"content":"Please restart the router and share the result."},
        headers=support_headers,
    )
    assert sent.status_code==201
    detail=client.get(f"/api/tickets/{ticket['id']}",headers=user_headers).json()
    assert detail["messages"][0]["author_role"]=="support"

def test_ticket_csv_export(client,user_headers,support_headers):
    client.post("/api/tickets",json=TICKET,headers=user_headers)
    response=client.get("/api/tickets/export.csv",headers=support_headers)
    assert response.status_code==200
    assert "text/csv" in response.headers["content-type"]
    assert "Office internet is down" in response.text

def test_login_returns_workspace_permissions(client):
    response=client.post(
        "/api/auth/login",
        data={"username":"user@test.com","password":"user123"},
    )
    assert response.status_code==200
    assert {"can_access_helpdesk","can_access_workspace","can_access_stock","can_request_stock"}.issubset(
        set(response.json()["user"]["permissions"])
    )

def test_regular_user_sees_allowed_operational_modules(client,user_headers):
    response=client.get("/api/modules",headers=user_headers)
    assert response.status_code==200
    assert [module["id"] for module in response.json()]==["helpdesk","inventory","stock","lan_messenger","sign","dashboards"]

def test_unauthorized_module_and_data_access_is_denied(client,user_headers,inventory_headers):
    assert client.get("/api/inventory/items",headers=user_headers).status_code==403
    assert client.get("/api/knowledge-base",headers=user_headers).status_code==403
    assert client.get("/api/tickets",headers=inventory_headers).status_code==403

def test_manager_can_view_helpdesk_dashboard(client,manager_headers):
    response=client.get("/api/dashboard/stats",headers=manager_headers)
    assert response.status_code==200
    assert response.json()["total_tickets"]==0

def test_ticket_user_and_knowledge_endpoints_are_paginated(client,user_headers,admin_headers):
    for number in range(3):
        client.post(
            "/api/tickets",
            json={**TICKET,"title":f"Network incident {number}"},
            headers=user_headers,
        )
    tickets=client.get(
        "/api/tickets?page=2&page_size=2",
        headers=user_headers,
    ).json()
    assert tickets["total"]==3
    assert tickets["page"]==2
    assert len(tickets["items"])==1
    users=client.get(
        "/api/users?page=1&page_size=2",
        headers=admin_headers,
    ).json()
    assert users["total"]==6
    assert len(users["items"])==2
    knowledge=client.get(
        "/api/knowledge-base?page=1&page_size=2",
        headers=admin_headers,
    ).json()
    assert knowledge["items"]==[]
    assert knowledge["pages"]==0

def test_workspace_summary_is_lightweight(client,user_headers):
    client.post("/api/tickets",json=TICKET,headers=user_headers)
    summary=client.get("/api/workspace/summary",headers=user_headers)
    assert summary.status_code==200
    data=summary.json()
    assert data["accessible_modules"]==6
    assert data["open_helpdesk_tickets"]==1
    assert data["my_ticket_count"]==1
    assert {"my_asset_count","my_stock_request_count","module_insights"}.issubset(data)
    assert len(data["recent_activity"])==1
    assert "description" not in data["recent_activity"][0]

def test_workspace_search_respects_inventory_access(client,inventory_headers,user_headers):
    assignees=client.get("/api/inventory/assignees?q=user",headers=inventory_headers).json()
    user_id=next(item["id"] for item in assignees if item["email"]=="user@test.com")
    inventory_id=next(item["id"] for item in client.get("/api/inventory/assignees?q=inventory",headers=inventory_headers).json() if item["email"]=="inventory@test.com")
    client.post("/api/inventory/items",json={
        "designation":"Latitude assigned laptop","category":"Computer","location":"Demo Field Office",
        "serial_number":"USER-LAT-001","number":"001","assigned_user_id":user_id,
    },headers=inventory_headers)
    client.post("/api/inventory/items",json={
        "designation":"Latitude hidden laptop","category":"Computer","location":"Demo Field Office",
        "serial_number":"HIDDEN-LAT-001","number":"002","assigned_user_id":inventory_id,
    },headers=inventory_headers)
    result=client.get("/api/workspace/search?q=Latitude",headers=user_headers)
    assert result.status_code==200
    titles=[item["title"] for item in result.json()["items"]]
    assert "Latitude assigned laptop" in titles
    assert "Latitude hidden laptop" not in titles

def test_page_load_does_not_run_ai_again(client,user_headers,monkeypatch):
    ticket=client.post("/api/tickets",json=TICKET,headers=user_headers).json()
    def unexpected_triage(*args,**kwargs):
        raise AssertionError("AI triage ran during a read request")
    monkeypatch.setattr(AITriageService,"triage",unexpected_triage)
    assert client.get("/api/tickets",headers=user_headers).status_code==200
    assert client.get(f"/api/tickets/{ticket['id']}",headers=user_headers).status_code==200

def test_audit_log_and_task_endpoints_are_paginated(client,admin_headers,support_headers):
    audit=client.get("/api/audit-logs?page=1&page_size=5",headers=admin_headers)
    assert audit.status_code==200
    assert audit.json()["page_size"]==5
    tasks=client.get("/api/tasks?page=1&page_size=10",headers=support_headers)
    assert tasks.status_code==200
    assert tasks.json()=={"items":[],"total":0,"page":1,"page_size":10,"pages":0}

def test_inventory_creation_export_and_access_control(client,inventory_headers,user_headers):
    payload={"designation":"Dell Latitude 7450","category":"Computer","location":"Demo Field Office","serial_number":"SN-001","number":"DEMO-IT-001"}
    created=client.post("/api/inventory/items",json=payload,headers=inventory_headers)
    assert created.status_code==201
    exported=client.get("/api/inventory/items/export/csv",headers=inventory_headers)
    assert exported.status_code==200
    assert exported.text.startswith("\ufeffStatus,Country,Project,Category")
    assert "Dell Latitude 7450" in exported.text
    assert client.post("/api/inventory/items",json=payload,headers=user_headers).status_code==403

def test_stock_request_delivery_reduces_quantity(client,inventory_headers,user_headers):
    item=client.post("/api/stock/items",json={
        "item_name":"USB-C Adapter","category":"Accessories","quantity_available":10,
        "low_stock_threshold":2,"unit":"piece","location":"Demo Field Office"
    },headers=inventory_headers)
    assert item.status_code==201
    request=client.post("/api/stock/requests",json={
        "item_id":item.json()["id"],"requested_quantity":3,"location":"Demo Field Office","reason":"Laptop docking setup"
    },headers=user_headers)
    assert request.status_code==201
    request_id=request.json()["id"]
    assert client.patch(f"/api/stock/requests/{request_id}",json={"status":"Approved"},headers=inventory_headers).status_code==200
    delivered=client.patch(f"/api/stock/requests/{request_id}",json={"status":"Delivered"},headers=inventory_headers)
    assert delivered.status_code==200
    stock=client.get("/api/stock/items",headers=inventory_headers).json()["items"][0]
    assert stock["quantity_available"]==7
    assert client.patch(f"/api/stock/requests/{request_id}",json={"status":"Delivered"},headers=inventory_headers).status_code==409
    assert client.patch(f"/api/stock/requests/{request_id}",json={"status":"Approved"},headers=user_headers).status_code==403

def test_organization_branding_requires_permission(client,super_headers,user_headers):
    payload={"organization_name":"Demo Organization","organization_short_name":"DEMO","primary_color":"#245c4f","support_email":"ict@example.org","address":"Demo Field Office","footer_text":"Internal operations"}
    assert client.put("/api/organization-settings",json=payload,headers=user_headers).status_code==403
    updated=client.put("/api/organization-settings",json=payload,headers=super_headers)
    assert updated.status_code==200
    assert updated.json()["organization_name"]=="Demo Organization"

def test_profile_picture_validation(client,user_headers):
    invalid=client.post("/api/profile/picture",files={"file":("avatar.exe",b"MZ","application/octet-stream")},headers=user_headers)
    assert invalid.status_code==415
    valid=client.post("/api/profile/picture",files={"file":("avatar.png",b"\x89PNG\r\n\x1a\nprofile","image/png")},headers=user_headers)
    assert valid.status_code==200
    assert valid.json()["profile_picture_url"]

