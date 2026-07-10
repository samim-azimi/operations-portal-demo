import os
os.environ["DATABASE_URL"]="sqlite://"
os.environ["OPENAI_API_KEY"]=""
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base,get_db
from app.main import app
from app.middleware import request_limiter
from app.models import User,UserRole
from app.security import hash_password
SUPER_ADMIN_EMAIL="superadmin@operations-portal.demo"
engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
TestingSession=sessionmaker(bind=engine,autoflush=False,autocommit=False)
def override_db():
    db=TestingSession()
    try: yield db
    finally: db.close()
app.dependency_overrides[get_db]=override_db
@pytest.fixture(autouse=True)
def reset_db():
    request_limiter.reset()
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    db=TestingSession(); db.add_all([
        User(full_name="Admin",email="admin@test.com",password_hash=hash_password("admin123"),role=UserRole.ADMIN),
        User(full_name="Demo Admin",email=SUPER_ADMIN_EMAIL,password_hash=hash_password("admin123"),role=UserRole.SUPER_ADMIN),
        User(full_name="Support",email="support@test.com",password_hash=hash_password("support123"),role=UserRole.SUPPORT),
        User(full_name="Manager",email="manager@test.com",password_hash=hash_password("manager123"),role=UserRole.MANAGER),
        User(full_name="Inventory",email="inventory@test.com",password_hash=hash_password("inventory123"),role=UserRole.INVENTORY_OFFICER),
        User(full_name="User",email="user@test.com",password_hash=hash_password("user123"),role=UserRole.USER),
    ]); db.commit(); db.close()
@pytest.fixture
def client(): return TestClient(app)
def login(client,email,password): return client.post("/api/auth/login",data={"username":email,"password":password}).json()["access_token"]
@pytest.fixture
def user_headers(client): return {"Authorization":"Bearer "+login(client,"user@test.com","user123")}
@pytest.fixture
def support_headers(client): return {"Authorization":"Bearer "+login(client,"support@test.com","support123")}
@pytest.fixture
def admin_headers(client): return {"Authorization":"Bearer "+login(client,"admin@test.com","admin123")}
@pytest.fixture
def super_headers(client): return {"Authorization":"Bearer "+login(client,SUPER_ADMIN_EMAIL,"admin123")}
@pytest.fixture
def manager_headers(client): return {"Authorization":"Bearer "+login(client,"manager@test.com","manager123")}
@pytest.fixture
def inventory_headers(client): return {"Authorization":"Bearer "+login(client,"inventory@test.com","inventory123")}
