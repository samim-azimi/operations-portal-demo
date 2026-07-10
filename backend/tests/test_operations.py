from io import BytesIO
from pathlib import Path
from datetime import date

from openpyxl import Workbook

from app.models import InventoryItem, StockRequest, User
from conftest import TestingSession


def create_category(client, headers, name="Stationery", active=True):
    response=client.post("/api/stock/categories",json={
        "name":name,"description":f"{name} materials","icon":"Package",
        "display_order":1,"is_active":active,
    },headers=headers)
    assert response.status_code==201
    return response.json()


def create_stock_item(client, headers, category, name="Notebook", quantity=20):
    response=client.post("/api/stock/items",json={
        "item_name":name,"category":category["name"],"category_id":category["id"],
        "quantity_available":quantity,"low_stock_threshold":3,"unit":"piece",
        "location":"Demo Field Office","unit_price":100,"currency":"AFN",
    },headers=headers)
    assert response.status_code==201
    return response.json()


def test_module_order_and_asset_management_removed(client,super_headers):
    modules=client.get("/api/modules",headers=super_headers).json()
    ids=[item["id"] for item in modules]
    assert ids==["helpdesk","inventory","stock","lan_messenger","sign","tasks","knowledge","documents","procurement","calendar","reports","dashboards","admin"]
    assert "assets" not in ids
    assert modules[1]["name"]=="Inventory Management System"
    assert modules[2]["name"]=="Stock Management System"
    assert ids.index("dashboards")==ids.index("reports")+1


def test_my_assets_only_returns_current_users_assets(client,user_headers,inventory_headers):
    db=TestingSession()
    user=db.query(User).filter_by(email="user@test.com").one()
    other=db.query(User).filter_by(email="manager@test.com").one()
    db.add_all([
        InventoryItem(status="Allocated",country="DEMO",project="DEMO",category="ITE",number="001",designation="Assigned laptop",location="Demo Field Office",assigned_user_id=user.id,created_by_id=1),
        InventoryItem(status="Allocated",country="DEMO",project="DEMO",category="ITE",number="002",designation="Managers laptop",location="Demo Field Office",assigned_user_id=other.id,created_by_id=1),
    ]);db.commit();db.close()
    response=client.get("/api/inventory/my-assets",headers=user_headers)
    assert response.status_code==200
    assert [item["designation"] for item in response.json()["items"]]==["Assigned laptop"]


def test_asset_form_endpoints_are_unavailable_in_public_demo(client,user_headers,inventory_headers):
    db=TestingSession();user=db.query(User).filter_by(email="user@test.com").one();user_id=user.id
    db.add(InventoryItem(status="Allocated",country="DEMO",project="DEMO",category="ITE",number="003",designation="Demo laptop",location="Demo Field Office",assigned_user_id=user.id,serial_number="ASSET-003",created_by_id=1))
    db.commit();db.close()
    message="Asset Form export is not available in the public demo."
    for method,path in [
        ("get",f"/api/inventory/asset-form/preview?user_id={user_id}"),
        ("get",f"/api/inventory/asset-form/export/pdf?user_id={user_id}"),
        ("get",f"/api/inventory/asset-form/signing-status?user_id={user_id}"),
        ("post",f"/api/inventory/asset-form/signing-request?user_id={user_id}&phase=allocation"),
    ]:
        response=getattr(client,method)(path,headers=inventory_headers)
        assert response.status_code==404
        assert response.json()["detail"]==message
    assert client.get("/api/inventory/my-assets",headers=user_headers).status_code==200


def test_inventory_logistics_code_status_and_export_format(client,inventory_headers):
    payload={
        "status":"In Stock","country":"DEMO","project":"21046","category":"OF",
        "sub_category":"LAP","number":"001","designation":"Latitude laptop",
        "location":"Demo Field Office","serial_number":"SLASH-001",
    }
    created=client.post("/api/inventory/items",json=payload,headers=inventory_headers)
    assert created.status_code==201
    assert created.json()["logistics_code"]=="DEMO/21046/OF/LAP/001"
    invalid=client.post(
        "/api/inventory/items",
        json={**payload,"status":"Active","serial_number":"SLASH-002","number":"002"},
        headers=inventory_headers,
    )
    assert invalid.status_code==422
    exported=client.get("/api/inventory/items/export/csv",headers=inventory_headers)
    assert exported.status_code==200
    assert "Logistics Code" not in exported.text
    assert "DEMO/21046/OF/LAP/001" not in exported.text
    round_trip=client.post(
        "/api/inventory/items/import",
        files={"file":("inventory-register.csv",exported.content,"text/csv")},
        headers=inventory_headers,
    )
    assert round_trip.status_code==200
    assert round_trip.json()["total"]==1
    assert round_trip.json()["skipped"]==1
    inventory_ui=(Path(__file__).resolve().parents[2]/"frontend/src/pages/Inventory.jsx").read_text(encoding="utf-8")
    assert '.filter(Boolean).join("/")' in inventory_ui
    assert 'const inventoryStatuses=["In Stock","Allocated","Out of Inventory"]' in inventory_ui


def test_inventory_csv_and_xlsx_import_preview_confirm_and_permissions(
    client,inventory_headers,user_headers,
):
    csv_content=(
        "Status,Country,Project,Category,Sub-Category,Number,"
        "Designation,Serial number,\"Location (Coo, Base 1 etc.)\",User,Remarks\n"
        "Allocated,DEMO,21046,OF,LAP,009,"
        "Imported laptop,IMPORT-009,Demo Field Office,user@test.com,Imported note\n"
        "Invalid,DEMO,21046,OF,LAP,010,"
        "Invalid status laptop,IMPORT-010,Demo Field Office,,\n"
    )
    preview=client.post(
        "/api/inventory/items/import",
        files={"file":("inventory.csv",csv_content.encode(),"text/csv")},
        headers=inventory_headers,
    )
    assert preview.status_code==200
    assert preview.json()["total"]==2
    assert preview.json()["valid"]==1
    assert preview.json()["invalid"]==1
    confirmed=client.post(
        "/api/inventory/items/import?confirm=true",
        files={"file":("inventory.csv",csv_content.encode(),"text/csv")},
        headers=inventory_headers,
    )
    assert confirmed.status_code==200
    assert confirmed.json()["imported"]==1
    assert client.post(
        "/api/inventory/items/import",
        files={"file":("inventory.csv",csv_content.encode(),"text/csv")},
        headers=user_headers,
    ).status_code==403

    workbook=Workbook()
    sheet=workbook.active
    sheet.append(["Status","Country","Project","Category","Sub-Category","Number","Designation","Serial number","Location (Coo, Base 1 etc)"])
    sheet.append(["In Stock","DEMO","21046","OF","MON","011","Monitor","IMPORT-011","Demo Field Office"])
    stream=BytesIO();workbook.save(stream)
    xlsx=client.post(
        "/api/inventory/items/import",
        files={"file":("inventory.xlsx",stream.getvalue(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=inventory_headers,
    )
    assert xlsx.status_code==200
    assert xlsx.json()["valid"]==1


def test_my_assets_is_identity_scoped_even_for_super_admin(client,super_headers):
    db=TestingSession()
    super_user=db.query(User).filter_by(email="superadmin@operations-portal.demo").one()
    other=db.query(User).filter_by(email="user@test.com").one()
    db.add_all([
        InventoryItem(status="Allocated",category="ITE",designation="Super laptop",location="Demo Field Office",assigned_user_id=super_user.id,created_by_id=1),
        InventoryItem(status="Allocated",category="ITE",designation="Other laptop",location="Demo Field Office",assigned_user_id=other.id,created_by_id=1),
        InventoryItem(status="Allocated",category="ITE",designation="Legacy name match",location="Demo Field Office",user_name=super_user.full_name,created_by_id=1),
    ])
    db.commit();db.close()
    response=client.get("/api/inventory/my-assets",headers=super_headers)
    assert response.status_code==200
    assert [item["designation"] for item in response.json()["items"]]==["Super laptop"]


def test_stock_categories_filter_items_and_hide_inactive(client,user_headers,inventory_headers):
    stationery=create_category(client,inventory_headers,"Stationery")
    cleaning=create_category(client,inventory_headers,"Cleaning Materials")
    create_stock_item(client,inventory_headers,stationery,"Blue pen")
    create_stock_item(client,inventory_headers,cleaning,"Cleaning cloth")
    items=client.get(f"/api/stock/categories/{stationery['id']}/items",headers=user_headers).json()["items"]
    assert [item["item_name"] for item in items]==["Blue pen"]
    client.patch(f"/api/stock/categories/{cleaning['id']}/deactivate",headers=inventory_headers)
    names=[item["name"] for item in client.get("/api/stock/categories",headers=user_headers).json()]
    assert names==["Stationery"]


def test_my_requests_never_returns_another_users_request(client,user_headers,super_headers,inventory_headers):
    category=create_category(client,inventory_headers)
    item=create_stock_item(client,inventory_headers,category)
    user_request=client.post("/api/stock/requests",json={"item_id":item["id"],"requested_quantity":1,"location":"Demo Field Office","reason":"User work"},headers=user_headers)
    admin_request=client.post("/api/stock/requests",json={"item_id":item["id"],"requested_quantity":1,"location":"Demo Field Office","reason":"Admin work"},headers=super_headers)
    assert user_request.status_code==201 and admin_request.status_code==201
    own=client.get("/api/stock/requests/my",headers=super_headers).json()["items"]
    assert [row["request_number"] for row in own]==[admin_request.json()["request_number"]]
    all_rows=client.get("/api/stock/requests",headers=super_headers).json()["items"]
    assert {row["request_number"] for row in all_rows}=={user_request.json()["request_number"],admin_request.json()["request_number"]}
    assert client.get("/api/stock/requests",headers=user_headers).status_code==403


def test_stock_card_number_validation_generation_uniqueness_and_export(client,inventory_headers):
    category=create_category(client,inventory_headers)
    item=create_stock_item(client,inventory_headers,category)
    generated=client.get("/api/stock/stock-cards/generate-number?base=coo&location=wh1",headers=inventory_headers)
    assert generated.status_code==200 and generated.json()["stock_card_number"]=="COO.WH1.001"
    payload={"base":"COO","storage_location":"WH1","sequence_number":"001","stock_item_id":item["id"],"unit":"piece","unit_price":100,"currency":"AFN"}
    created=client.post("/api/stock/stock-cards",json=payload,headers=inventory_headers)
    assert created.status_code==201 and created.json()["stock_card_number"]=="COO.WH1.001"
    assert client.post("/api/stock/stock-cards",json=payload,headers=inventory_headers).status_code==409
    assert client.post("/api/stock/stock-cards",json={**payload,"base":"CO"},headers=inventory_headers).status_code==422
    exported=client.get("/api/stock/stock-cards/export/csv",headers=inventory_headers)
    assert exported.status_code==200
    assert "Base,Location of Storage,Number,Stock Card Number" in exported.text


def test_stock_card_movement_and_annual_reports_calculate_balances(client,inventory_headers):
    category=create_category(client,inventory_headers)
    item=create_stock_item(client,inventory_headers,category,quantity=20)
    card=client.post("/api/stock/stock-cards",json={"base":"COO","storage_location":"WH1","sequence_number":"108","stock_item_id":item["id"],"unit":"piece","unit_price":10,"currency":"AFN","opening_quantity":5},headers=inventory_headers).json()
    for movement_type,quantity_in,quantity_out,movement_date in [("IN",10,0,"2025-01-05"),("OUT",0,3,"2025-02-07")]:
        response=client.post("/api/stock/movements",json={"stock_item_id":item["id"],"stock_card_id":card["id"],"movement_date":movement_date,"movement_type":movement_type,"quantity_in":quantity_in,"quantity_out":quantity_out,"mission":"DEMO MISSION","base":"COORDINATION"},headers=inventory_headers)
        assert response.status_code==201
    card_preview=client.get(f"/api/stock/reports/stock-card/preview?card_id={card['id']}&from_date=2025-02-01&to_date=2025-02-28",headers=inventory_headers).json()
    assert card_preview["previous_balance"]==15
    assert card_preview["final_balance"]==12
    movement_csv=client.get("/api/stock/reports/movements/export/csv?year=2025",headers=inventory_headers)
    assert "Date mouvement JJ/MM/AAAA,Month Number,IN,OUT" in movement_csv.text
    assert "05/01/2025,1,10.0,0" in movement_csv.text
    annual=client.get("/api/stock/reports/annual-summary/preview?year=2025",headers=inventory_headers).json()["items"][0]
    assert annual["months"][0]["theoritical_quantity"]==15
    assert annual["months"][1]["theoritical_quantity"]==12
    assert annual["months"][1]["total_value"]==120


def test_theme_and_logo_permissions(client,user_headers,super_headers):
    payload={"organization_name":"Test Organization","organization_short_name":"TEST","primary_color":"#0f9f72","theme_id":"emerald-green","support_email":"support@example.org","address":"Demo Field Office","footer_text":"Operations"}
    assert client.put("/api/organization-settings",json=payload,headers=user_headers).status_code==403
    assert client.post("/api/organization-settings/logo",files={"file":("logo.png",b"\x89PNG\r\n\x1a\nlogo","image/png")},headers=user_headers).status_code==403
    assert client.post("/api/organization-settings/collapsed-sidebar-icon",files={"file":("icon.png",b"\x89PNG\r\n\x1a\nicon","image/png")},headers=user_headers).status_code==403
    saved=client.put("/api/organization-settings",json=payload,headers=super_headers)
    assert saved.status_code==200 and saved.json()["theme_id"]=="emerald-green"
    logo=client.post("/api/organization-settings/logo",files={"file":("logo.png",b"\x89PNG\r\n\x1a\nlogo","image/png")},headers=super_headers)
    assert logo.status_code==200 and logo.json()["logo_url"]
    served=client.get(logo.json()["logo_url"])
    assert served.status_code==200 and served.content==b"\x89PNG\r\n\x1a\nlogo"
    assert served.headers["cache-control"]=="no-store"
    assert served.headers["cross-origin-resource-policy"]=="cross-origin"
    small=client.post("/api/organization-settings/collapsed-sidebar-icon",files={"file":("icon.png",b"\x89PNG\r\n\x1a\nicon","image/png")},headers=super_headers)
    assert small.status_code==200 and small.json()["collapsed_sidebar_icon_url"]
    assert client.get(small.json()["collapsed_sidebar_icon_url"]).content==b"\x89PNG\r\n\x1a\nicon"
    current=client.get("/api/organization-settings").json()
    assert current["logo_url"] and current["collapsed_sidebar_icon_url"]
    assert client.delete("/api/organization-settings/logo",headers=super_headers).status_code==204
    assert client.delete("/api/organization-settings/collapsed-sidebar-icon",headers=super_headers).status_code==204
    cleared=client.get("/api/organization-settings").json()
    assert cleared["logo_url"] is None and cleared["collapsed_sidebar_icon_url"] is None


def test_default_brand_assets_and_workspace_avatar_placement():
    root=Path(__file__).resolve().parents[2]
    for name in ("operations-portal-app-icon.png","operations-sidebar-icon.png"):
        assert (root/"frontend/public/assets/branding"/name).is_file()
    workspace=(root/"frontend/src/pages/Workspace.jsx").read_text(encoding="utf-8")
    layout=(root/"frontend/src/components/Layout.jsx").read_text(encoding="utf-8")
    assert "UserAvatar" not in workspace
    assert '<UserAvatar user={user} className="small"/>' in layout


def test_dashboard_role_and_user_access(client,user_headers,manager_headers,super_headers):
    db=TestingSession();user_id=db.query(User).filter_by(email="user@test.com").one().id;db.close()
    created=client.post("/api/dashboards",json={"title":"Operations","description":"Power BI","embed_url":"https://example.com/demo-dashboard","provider":"Power BI","is_active":True,"allowed_roles":["manager"],"user_ids":[user_id]},headers=super_headers)
    assert created.status_code==201
    assert client.get("/api/dashboards/my",headers=user_headers).json()["total"]==1
    assert client.get("/api/dashboards/my",headers=manager_headers).json()["total"]==1
    assert client.get("/api/dashboards",headers=user_headers).status_code==403

