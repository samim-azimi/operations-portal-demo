from __future__ import annotations

from dataclasses import asdict, dataclass

from app.models import UserRole


@dataclass(frozen=True)
class WorkspaceModule:
    id: str
    name: str
    short_name: str
    description: str
    icon: str
    route: str
    status: str
    required_permission: str
    category: str


# This order is the product navigation contract.
MODULES = [
    WorkspaceModule("helpdesk", "Help Desk", "Help Desk", "Create, track, triage, and resolve support requests.", "LifeBuoy", "/helpdesk", "active", "can_access_helpdesk", "Operations"),
    WorkspaceModule("inventory", "Inventory Management System", "IMS", "Manage inventory assets, user assignments, and valuation.", "PackageSearch", "/inventory", "active", "can_access_inventory", "Assets"),
    WorkspaceModule("stock", "Stock Management System", "Stock", "Manage stock items, employee requests, stock cards, movements, and reports.", "Warehouse", "/stock", "active", "can_access_stock", "Operations"),
    WorkspaceModule("lan_messenger", "LAN Messenger", "LAN Messenger", "LAN-first direct, group, and channel messaging with meetings and call sessions.", "MessagesSquare", "/lan-messenger", "active", "can_access_lan_messenger", "Communication"),
    WorkspaceModule("sign", "Sign", "Sign", "Internal document signing with secure links, envelope IDs, hashes, and audit trails.", "FileSignature", "/sign", "active", "can_access_sign", "Governance"),
    WorkspaceModule("tasks", "Tasks", "Tasks", "Coordinate work, ownership, priorities, and due dates.", "ListChecks", "/tasks", "active", "can_access_tasks", "Operations"),
    WorkspaceModule("knowledge", "Knowledge", "Knowledge", "Find approved solutions and reusable operational guidance.", "BookOpen", "/knowledge", "active", "can_access_knowledge", "Knowledge"),
    WorkspaceModule("documents", "Documents", "Documents", "Store, organize, and search controlled documents.", "FolderKanban", "/documents", "coming_soon", "can_access_documents", "Knowledge"),
    WorkspaceModule("procurement", "Procurement", "Procurement", "Track PRs, RFQs, purchase orders, deliveries, and payments.", "ShoppingCart", "/procurement", "coming_soon", "can_access_procurement", "Operations"),
    WorkspaceModule("calendar", "Calendar", "Calendar", "Manage meetings, reminders, maintenance, and support visits.", "CalendarDays", "/calendar", "coming_soon", "can_access_calendar", "Productivity"),
    WorkspaceModule("reports", "Reports", "Reports", "Generate cross-module operational reports.", "ChartNoAxesCombined", "/reports", "coming_soon", "can_access_reports", "Insights"),
    WorkspaceModule("dashboards", "Dashboards", "Dashboards", "View assigned published dashboards and Power BI reports.", "LayoutDashboard", "/dashboards", "active", "can_access_dashboards", "Insights"),
    WorkspaceModule("admin", "Admin Center", "Admin Center", "Manage users, access, branding, themes, and governance.", "ShieldCheck", "/admin", "active", "can_access_admin", "Administration"),
]

ALL_MODULE_PERMISSIONS = {module.required_permission for module in MODULES}
STOCK_USER_PERMISSIONS = {
    "can_access_stock", "can_request_stock", "can_view_own_stock_requests",
    "can_access_stock_categories",
}
INVENTORY_USER_PERMISSIONS = {"can_access_inventory", "can_view_own_assets"}
INVENTORY_MANAGEMENT_PERMISSIONS = {
    "can_manage_inventory", "can_export_inventory", "can_import_inventory",
}
STOCK_MANAGEMENT_PERMISSIONS = {
    "can_manage_stock", "can_import_stock", "can_approve_stock_requests",
    "can_export_stock", "can_view_all_stock_requests", "can_manage_stock_requests",
    "can_manage_stock_categories", "can_access_stock_cards", "can_manage_stock_cards",
    "can_export_stock_cards", "can_export_stock_card", "can_export_stock_movements",
    "can_export_annual_stock_summary",
}
ADMIN_PERMISSIONS = {
    "can_manage_helpdesk", "can_manage_users", "can_manage_permissions",
    "can_manage_organization_branding", "can_manage_themes", "can_manage_dashboards",
    "can_view_all_dashboards",
}
SIGN_USER_PERMISSIONS = {
    "can_access_sign", "can_sign_documents", "can_view_own_signature_requests",
    "can_download_signed_documents", "can_verify_signed_documents",
    "can_upload_own_signature",
}
SIGN_CREATOR_PERMISSIONS = {
    "can_create_signature_envelope", "can_send_signature_envelope",
    "can_cancel_signature_envelope",
}
SIGN_ADMIN_PERMISSIONS = {
    "can_view_all_signature_envelopes", "can_manage_sign_settings",
    "can_manage_user_signatures",
}
LAN_USER_PERMISSIONS = {
    "can_access_lan_messenger", "can_send_lan_messages", "can_create_lan_groups",
    "can_create_lan_channels", "can_upload_lan_attachments",
    "can_schedule_lan_meetings", "can_join_lan_meetings",
    "can_start_lan_voice_call", "can_start_lan_video_call",
    "can_start_lan_group_voice_call", "can_start_lan_group_video_call",
}
LAN_ADMIN_PERMISSIONS = {
    "can_manage_lan_groups", "can_manage_lan_channels",
    "can_manage_lan_meetings", "can_manage_lan_messenger_settings",
}
ALL_PERMISSIONS = {
    "can_access_workspace", *ALL_MODULE_PERMISSIONS, *STOCK_USER_PERMISSIONS,
    *INVENTORY_USER_PERMISSIONS, *INVENTORY_MANAGEMENT_PERMISSIONS,
    *STOCK_MANAGEMENT_PERMISSIONS, *ADMIN_PERMISSIONS, *SIGN_USER_PERMISSIONS,
    *SIGN_CREATOR_PERMISSIONS, *SIGN_ADMIN_PERMISSIONS,
    *LAN_USER_PERMISSIONS, *LAN_ADMIN_PERMISSIONS,
}

ROLE_PERMISSIONS = {
    UserRole.USER: {"can_access_workspace", "can_access_helpdesk", "can_access_dashboards", *INVENTORY_USER_PERMISSIONS, *STOCK_USER_PERMISSIONS, *SIGN_USER_PERMISSIONS, *LAN_USER_PERMISSIONS},
    UserRole.SUPPORT: {"can_access_workspace", "can_access_helpdesk", "can_access_knowledge", "can_access_tasks", "can_access_dashboards", *SIGN_USER_PERMISSIONS, *LAN_USER_PERMISSIONS},
    UserRole.MANAGER: {
        "can_access_workspace", "can_access_helpdesk", "can_access_tasks",
        "can_access_reports", "can_access_dashboards", *STOCK_USER_PERMISSIONS, *SIGN_USER_PERMISSIONS, *LAN_USER_PERMISSIONS,
    },
    UserRole.INVENTORY_OFFICER: {
        "can_access_workspace", *INVENTORY_USER_PERMISSIONS, *INVENTORY_MANAGEMENT_PERMISSIONS,
        *STOCK_USER_PERMISSIONS, *STOCK_MANAGEMENT_PERMISSIONS, "can_access_dashboards",
        *SIGN_USER_PERMISSIONS, *SIGN_CREATOR_PERMISSIONS, *LAN_USER_PERMISSIONS,
    },
    UserRole.STOCK_MANAGER: {
        "can_access_workspace", *STOCK_USER_PERMISSIONS, *STOCK_MANAGEMENT_PERMISSIONS, "can_access_dashboards", *SIGN_USER_PERMISSIONS,
    },
    UserRole.ADMIN: {
        "can_access_workspace", *ALL_MODULE_PERMISSIONS, *INVENTORY_USER_PERMISSIONS,
        *INVENTORY_MANAGEMENT_PERMISSIONS, *STOCK_USER_PERMISSIONS,
        *STOCK_MANAGEMENT_PERMISSIONS, *ADMIN_PERMISSIONS, *SIGN_USER_PERMISSIONS,
        *SIGN_CREATOR_PERMISSIONS, *SIGN_ADMIN_PERMISSIONS,
        *LAN_USER_PERMISSIONS, *LAN_ADMIN_PERMISSIONS,
    },
    UserRole.SUPER_ADMIN: ALL_PERMISSIONS,
}


def permissions_for_role(role: UserRole) -> set[str]:
    return set(ROLE_PERMISSIONS.get(role, set()))


def module_payload(module: WorkspaceModule) -> dict:
    return asdict(module)
