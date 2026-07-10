from app.models import AuditLog
def record_audit(db,action,actor_id=None,ticket_id=None,details=None):
    db.add(AuditLog(action=action,actor_id=actor_id,ticket_id=ticket_id,details=details or {}))
