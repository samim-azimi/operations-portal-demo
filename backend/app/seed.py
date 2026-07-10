from app.database import Base,SessionLocal,engine
from datetime import date
from app.models import AuditLog,Dashboard,InventoryItem,KnowledgeBaseArticle,Priority,StockCard,StockCategory,StockItem,StockMovement,SupportLocation,Ticket,TicketAIAnalysis,TicketCategory,TicketNote,TicketStatus,User,UserRole
from app.security import hash_password
from app.services.knowledge_search import index_article

SUPER_ADMIN_EMAIL="superadmin@operations-portal.demo"

ARTICLES=[
("Internet is slow","Network","Websites and cloud apps load slowly.","Check affected scope, run a wired speed test, restart the adapter, and escalate with results.",["internet","slow","network"]),
("Outlook cannot connect","Email","Outlook shows disconnected or cannot reach Microsoft 365.","Check service health and connectivity, restart Outlook, then test a new profile.",["outlook","email","m365"]),
("Printer not printing","Printer","Jobs remain queued or the printer produces no output.","Check paper, toner and errors; clear the queue; confirm the correct driver and printer.",["printer","queue","toner"]),
("Laptop is overheating","Hardware","Laptop fan is loud, chassis is hot, or shutdowns occur.","Move to a hard surface, clean vents, check CPU use, update firmware, and run diagnostics.",["laptop","heat","fan"]),
("Cannot login to Microsoft 365","Account","A user cannot sign in to Microsoft 365.","Verify identity, check lockout and license status, then use the approved password reset process.",["login","m365","password"]),
("VPN is not connecting","Network","Remote user receives a VPN connection error.","Confirm internet access, credentials, time, and client version; collect the exact error for Network Team.",["vpn","remote","network"]),
("Wi-Fi keeps disconnecting","Network","Wireless connection drops repeatedly.","Forget and rejoin the network, update the adapter driver, and compare another access point.",["wifi","disconnect","wireless"]),
("Shared folder is not opening","Account","A mapped drive or shared folder is inaccessible.","Confirm network/VPN, validate the path, and have the owner verify group permissions.",["folder","permissions","share"]),
("Computer is very slow","Hardware","General workstation performance is degraded.","Restart, check disk space and startup load, run approved diagnostics, and review recent changes.",["slow","performance","computer"]),
("CCTV camera is offline","Network","A CCTV camera is unreachable from monitoring.","Check power/PoE and switch link, ping the camera, verify VLAN configuration, then escalate.",["cctv","camera","offline"])]
TICKETS=[
("VPN fails from home","VPN client says connection timed out","High"),("Printer queue stuck","Finance printer has five jobs stuck","Medium"),("Suspicious email received","User clicked a possible phishing link","Critical"),("Outlook disconnected","Outlook cannot connect since this morning","High"),("Laptop running hot","Fan is loud and laptop powers off","Medium"),("Password rejected","Microsoft 365 login says password incorrect","High"),("Office internet slow","Internet is slow for everyone in the demo field office","Critical"),("Wi-Fi drops","Wi-Fi keeps disconnecting in meeting room","Medium"),("Shared drive denied","Shared folder is not opening for my account","Medium"),("PC performance","Computer is very slow after update","Low"),("Camera offline","CCTV camera is offline at reception","High"),("Teams will not open","Microsoft Teams application crashes","Medium"),("Monitor flickers","External screen flickers intermittently","Low"),("Software install","Need approved PDF editor installed","Low"),("Scanner unavailable","Printer scan option cannot find my email","Medium")]
CATEGORIES=["Microsoft 365","Meeting rooms","Telephony / Phone system","Computer / Laptop","Software","Lists / Groups","Hardware / Equipment","Network access","Cybersecurity","Building access","Building maintenance","Events","Archiving"]
LOCATIONS=["Remote","Demo Field Office","Demo Warehouse","Demo Training Room","Demo Guest House"]
STOCK_CATEGORIES=[
    ("Stationery","Pens, notebooks, files, and everyday desk supplies","NotebookPen"),
    ("Consumables","Frequently consumed workplace materials","Boxes"),
    ("Small IT Materials","Mice, keyboards, adapters, cables, and flash drives","Mouse"),
    ("Office Supplies","General shared office supplies","BriefcaseBusiness"),
    ("Printer Supplies","Toner, drums, labels, and printer consumables","Printer"),
    ("Cleaning Materials","Approved office and facility cleaning materials","SprayCan"),
    ("Safety Materials","Protective and workplace safety materials","ShieldCheck"),
    ("Communication Materials","Radios, headsets, and communication accessories","Radio"),
    ("Electrical Materials","Power strips, batteries, and electrical accessories","PlugZap"),
    ("Other","Items that do not fit another active category","Package"),
]

def seed():
    Base.metadata.create_all(bind=engine); db=SessionLocal()
    try:
        demo_users=[
            ("Demo Admin",SUPER_ADMIN_EMAIL,"admin123",UserRole.SUPER_ADMIN,"Operations"),
            ("Demo Manager","manager@example.com","manager123",UserRole.MANAGER,"Operations"),
            ("Demo Inventory Officer","inventory@example.com","inventory123",UserRole.INVENTORY_OFFICER,"Logistics"),
            ("Demo Stock Officer","stock@example.com","stock123",UserRole.STOCK_MANAGER,"Logistics"),
            ("Demo User","user@example.com","user123",UserRole.USER,"Field Operations"),
        ]
        for full_name,email,password,role,department in demo_users:
            account=db.query(User).filter_by(email=email).first()
            if not account and role == UserRole.SUPER_ADMIN:
                account=db.query(User).filter_by(role=UserRole.SUPER_ADMIN).first()
            if account:
                account.full_name=full_name; account.email=email; account.role=role; account.department=department; account.is_active=True
            else:
                db.add(User(full_name=full_name,email=email,password_hash=hash_password(password),role=role,department=department))
        db.commit()
        admin=db.query(User).filter_by(email=SUPER_ADMIN_EMAIL).first(); regular=db.query(User).filter_by(email="user@example.com").first(); support=admin
        existing_categories={item.name:item for item in db.query(TicketCategory).all()}
        for name in CATEGORIES:
            if name in existing_categories:
                existing_categories[name].is_active=True
            else:
                db.add(TicketCategory(name=name,description=f"{name} support requests",is_active=True))
        for name,item in existing_categories.items():
            if name not in CATEGORIES:
                item.is_active=False
        existing_locations={item.name:item for item in db.query(SupportLocation).all()}
        for order,name in enumerate(LOCATIONS):
            if name in existing_locations:
                existing_locations[name].is_active=True; existing_locations[name].sort_order=order
            else:
                db.add(SupportLocation(name=name,is_active=True,sort_order=order))
        db.commit()
        if db.query(InventoryItem).count()==0:
            db.add_all([
                InventoryItem(status="Allocated",country="Demo Country",project="Demo Project",category="IT Equipment",sub_category="Laptop",number="DEMO-001",designation="Demo Laptop",brand="DemoBrand",model="DemoBook 14",serial_number="DEMO-LAPTOP-001",location="Demo Field Office",user_name="Demo User",assigned_user_id=regular.id,condition="Good",currency="USD",purchase_value_euros="1200",depreciation_period="36",accessories="Demo charger and laptop bag",created_by_id=admin.id),
                InventoryItem(status="In Stock",country="Demo Country",project="Demo Project",category="IT Equipment",sub_category="Printer",number="DEMO-002",designation="Demo Printer",brand="DemoBrand",model="DemoPrint 200",serial_number="DEMO-PRINTER-001",location="Demo Warehouse",condition="Good",currency="USD",created_by_id=admin.id),
            ])
        stock_category_map={}
        for order,(name,description,icon) in enumerate(STOCK_CATEGORIES):
            category=db.query(StockCategory).filter_by(name=name).first()
            if not category:
                category=StockCategory(name=name,description=description,icon=icon,display_order=order,created_by_id=admin.id,updated_by_id=admin.id)
                db.add(category);db.flush()
            stock_category_map[name]=category
        if db.query(StockItem).count()==0:
            db.add_all([
                StockItem(item_name="Demo Mouse",category="Small IT Materials",category_id=stock_category_map["Small IT Materials"].id,specifications="Demo 2.4 GHz USB receiver",quantity_available=24,low_stock_threshold=5,unit="piece",location="Demo Warehouse",status="Available",unit_price=10,currency="USD",donor="Demo Donor",project_code="Demo Project"),
                StockItem(item_name="Demo Toner",category="Printer Supplies",category_id=stock_category_map["Printer Supplies"].id,specifications="Demo black toner cartridge",quantity_available=4,low_stock_threshold=5,unit="cartridge",location="Demo Warehouse",status="Low Stock",unit_price=45,currency="USD",donor="Demo Donor",project_code="Demo Project"),
            ])
        db.commit()
        for item in db.query(StockItem).filter(StockItem.category_id.is_(None)).all():
            category=stock_category_map.get(item.category) or stock_category_map["Other"]
            item.category_id=category.id;item.category=category.name
        db.commit()
        if db.query(StockCard).count()==0:
            first=db.query(StockItem).order_by(StockItem.id).first()
            card=StockCard(base="COO",storage_location="WH1",sequence_number="001",stock_card_number="COO.WH1.001",donor=first.donor or "Multi",project_code=first.project_code or "Multi Project",stock_item_id=first.id,specifications=first.specifications,unit=first.unit,unit_price=first.unit_price,currency=first.currency,opening_quantity=20,minimum_quantity=5,created_by_id=admin.id)
            db.add(card);db.flush()
            db.add_all([
                StockMovement(stock_item_id=first.id,stock_card_id=card.id,movement_type="IN",quantity_change=10,quantity_in=10,movement_date=date(2025,1,5),month_number=1,year=2025,goods_received_note_no="DEMO-GRN-001",mission="DEMO MISSION",base="FIELD OFFICE",performed_by_id=admin.id),
                StockMovement(stock_item_id=first.id,stock_card_id=card.id,movement_type="OUT",quantity_change=-6,quantity_out=6,movement_date=date(2025,2,10),month_number=2,year=2025,destination="Demo Department",mission="DEMO MISSION",base="FIELD OFFICE",performed_by_id=admin.id),
            ])
        if db.query(Dashboard).count()==0:
            db.add(Dashboard(title="Demo Operations Dashboard",description="Placeholder dashboard entry for public demo data only.",embed_url="https://example.com/demo-dashboard",provider="Demo",allowed_roles=["manager","admin","super_admin"],created_by_id=admin.id,updated_by_id=admin.id))
        db.commit()
        if db.query(KnowledgeBaseArticle).count()==0:
            for title,cat,problem,solution,tags in ARTICLES:
                article=KnowledgeBaseArticle(title=title,category=cat,problem_description=problem,solution=solution,tags=tags,created_by_id=admin.id); db.add(article); db.flush(); index_article(article)
            db.commit()
        if db.query(Ticket).count()==0:
            from app.services.ai_triage_service import AITriageService
            from app.services.knowledge_search import search_articles
            for i,(title,description,urgency) in enumerate(TICKETS):
                status=[TicketStatus.OPEN,TicketStatus.IN_PROGRESS,TicketStatus.WAITING,TicketStatus.RESOLVED,TicketStatus.CLOSED][i%5]
                ticket=Ticket(requester_id=regular.id,full_name=regular.full_name,email=regular.email,department="Field Operations",location="Demo Field Office",device_name=f"DEMO-ASSET-{1000+i}",title=title,description=description,urgency=urgency,status=status)
                db.add(ticket); db.flush(); similar=search_articles(db,title+" "+description); result,provider=AITriageService().triage(ticket,similar)
                ticket.category=result.category; ticket.priority=Priority(result.priority); ticket.assigned_team=result.recommended_team; ticket.human_approval_required=result.needs_human_approval; ticket.human_approved=status in {TicketStatus.RESOLVED,TicketStatus.CLOSED}; ticket.resolution_notes="Issue resolved using the documented support procedure." if ticket.human_approved else None
                db.add(TicketAIAnalysis(ticket_id=ticket.id,**result.model_dump(),similar_issues=similar,provider=provider)); db.add(AuditLog(actor_id=regular.id,ticket_id=ticket.id,action="Ticket created",details={"seed":True})); db.add(AuditLog(ticket_id=ticket.id,action="AI triage completed",details={"provider":provider}))
                if i%3==0: db.add(TicketNote(ticket_id=ticket.id,author_id=support.id,content="Initial diagnostics reviewed; follow-up recorded.",is_internal=True))
            db.commit()
    finally: db.close()
if __name__=="__main__": seed()
