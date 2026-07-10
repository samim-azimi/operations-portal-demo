from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ensure_performance_indexes():
    for table in Base.metadata.sorted_tables:
        for index in table.indexes:
            index.create(bind=engine, checkfirst=True)

def ensure_schema_compatibility():
    """Small additive migration bridge for existing development databases.

    Production deployments should use Alembic; this keeps the existing demo
    database usable without deleting any data.
    """
    additions = {
        "organization_settings": {
            "theme_id": "VARCHAR(40) DEFAULT 'operations-blue'",
        },
        "inventory_items": {
            "assigned_user_id": "INTEGER",
        },
        "stock_items": {
            "category_id": "INTEGER",
            "item_type": "VARCHAR(120)",
            "donor": "VARCHAR(120)",
            "project_code": "VARCHAR(120)",
            "unit_price": "FLOAT DEFAULT 0",
            "currency": "VARCHAR(20) DEFAULT 'AFN'",
            "expiration_date": "DATE",
        },
        "stock_movements": {
            "stock_card_id": "INTEGER",
            "movement_date": "DATE",
            "month_number": "INTEGER DEFAULT 1",
            "year": "INTEGER DEFAULT 2026",
            "quantity_in": "FLOAT DEFAULT 0",
            "quantity_out": "FLOAT DEFAULT 0",
            "po_number": "VARCHAR(120)",
            "waybill_number": "VARCHAR(120)",
            "goods_received_note_no": "VARCHAR(120)",
            "stock_transfer_no": "VARCHAR(120)",
            "destination": "VARCHAR(250)",
            "remarks": "TEXT",
            "comments": "TEXT",
            "signature_name": "VARCHAR(160)",
            "mission": "VARCHAR(120) DEFAULT 'DEMO MISSION'",
            "base": "VARCHAR(120) DEFAULT 'COORDINATION'",
            "source_reference_type": "VARCHAR(80)",
            "source_reference_id": "INTEGER",
            "updated_at": "TIMESTAMP",
        },
        "signature_recipients": {
            "signature_page": "INTEGER DEFAULT -1",
            "signature_x": "FLOAT DEFAULT 0.61",
            "signature_y": "FLOAT DEFAULT 0.06",
            "signature_width": "FLOAT DEFAULT 0.32",
            "signature_height": "FLOAT DEFAULT 0.16",
        },
    }
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table_name, columns in additions.items():
            if table_name not in tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl in columns.items():
                if column_name not in existing:
                    connection.execute(text(
                        f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {ddl}'
                    ))
        if "inventory_items" in tables:
            connection.execute(text(
                "UPDATE inventory_items SET status = 'In Stock' "
                "WHERE status IS NULL OR status = '' OR status IN ('Active', 'Available')"
            ))
        if "organization_settings" in tables:
            connection.execute(text(
                "UPDATE organization_settings "
                "SET organization_name = 'Mission Operations Portal', "
                "organization_short_name = 'Operations Portal' "
                "WHERE organization_name = 'Faza Workspace'"
            ))

