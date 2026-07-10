from fastapi import APIRouter, Depends, HTTPException

from app.models import User
from app.modules import MODULES, module_payload, permissions_for_role
from app.schemas import ModuleRead
from app.security import get_current_user

router = APIRouter(prefix="/modules", tags=["Workspace Modules"])


@router.get("", response_model=list[ModuleRead])
def list_accessible_modules(user: User = Depends(get_current_user)):
    permissions = permissions_for_role(user.role)
    return [
        module_payload(module)
        for module in MODULES
        if module.status != "hidden" and module.required_permission in permissions
    ]


@router.get("/{module_id}", response_model=ModuleRead)
def get_module(module_id: str, user: User = Depends(get_current_user)):
    module = next((item for item in MODULES if item.id == module_id), None)
    if not module or module.status == "hidden":
        raise HTTPException(404, "Module not found")
    if module.required_permission not in permissions_for_role(user.role):
        raise HTTPException(403, "You do not have access to this Faza module")
    return module_payload(module)
