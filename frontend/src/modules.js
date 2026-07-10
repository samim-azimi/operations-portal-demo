import {
  BookOpen, CalendarDays, ChartNoAxesCombined, FolderKanban,
  LayoutDashboard, LifeBuoy, ListChecks, MessagesSquare, PackageSearch,
  ShieldCheck, ShoppingCart, Warehouse, FileSignature,
} from "lucide-react";

// Product navigation order. Workspace and About are shell-level links.
export const moduleRegistry = [
  {id:"helpdesk",name:"Help Desk",shortName:"Help Desk",labelKey:"helpdesk",description:"Create, track, triage, and resolve support requests.",icon:LifeBuoy,route:"/helpdesk",activeRoutes:["/helpdesk","/tickets","/submit-ticket","/my-tickets","/dashboard"],status:"active",permission:"can_access_helpdesk",category:"Operations",sidebarGroup:"logistics",sidebarGroupOrder:4},
  {id:"inventory",name:"Inventory Management System",shortName:"IMS",labelKey:"inventory",description:"Manage inventory assets, user assignments, valuation, and asset forms.",icon:PackageSearch,route:"/inventory",status:"active",permission:"can_access_inventory",category:"Assets",sidebarGroup:"logistics",sidebarGroupOrder:1},
  {id:"stock",name:"Stock Management System",shortName:"Stock",labelKey:"stock",description:"Manage stock items, employee requests, stock cards, movements, and stock reports.",icon:Warehouse,route:"/stock",status:"active",permission:"can_access_stock",category:"Operations",sidebarGroup:"logistics",sidebarGroupOrder:2},
  {id:"lan_messenger",name:"LAN Messenger",shortName:"LAN Messenger",labelKey:"lanMessenger",description:"LAN-first direct, group, and channel messaging with meetings and call sessions.",icon:MessagesSquare,route:"/lan-messenger",status:"active",permission:"can_access_lan_messenger",category:"Communication"},
  {id:"sign",name:"Sign",shortName:"Sign",labelKey:"sign",description:"Internal document signing with secure links, envelope IDs, hashes, and audit trails.",icon:FileSignature,route:"/sign",status:"active",permission:"can_access_sign",category:"Governance"},
  {id:"tasks",name:"Tasks",shortName:"Tasks",labelKey:"tasks",description:"Coordinate work, ownership, priorities, and due dates.",icon:ListChecks,route:"/tasks",status:"active",permission:"can_access_tasks",category:"Operations"},
  {id:"knowledge",name:"Knowledge",shortName:"Knowledge",labelKey:"knowledge",description:"Find approved solutions and reusable operational guidance.",icon:BookOpen,route:"/knowledge",status:"active",permission:"can_access_knowledge",category:"Knowledge"},
  {id:"documents",name:"Documents",shortName:"Documents",labelKey:"documents",description:"Store, organize, and search controlled documents.",icon:FolderKanban,route:"/documents",status:"coming_soon",permission:"can_access_documents",category:"Knowledge"},
  {id:"procurement",name:"Procurement",shortName:"Procurement",labelKey:"procurement",description:"Track PRs, RFQs, purchase orders, deliveries, and payments.",icon:ShoppingCart,route:"/procurement",status:"coming_soon",permission:"can_access_procurement",category:"Operations",sidebarGroup:"logistics",sidebarGroupOrder:3},
  {id:"calendar",name:"Events",shortName:"Events",labelKey:"calendar",description:"Manage public holidays, events, reminders, maintenance, and support visits.",icon:CalendarDays,route:"/events",activeRoutes:["/events","/calendar"],status:"coming_soon",permission:"can_access_calendar",category:"Productivity"},
  {id:"reports",name:"Reports",shortName:"Reports",labelKey:"reports",description:"Generate cross-module operational reports.",icon:ChartNoAxesCombined,route:"/reports",status:"coming_soon",permission:"can_access_reports",category:"Insights"},
  {id:"dashboards",name:"Dashboards",shortName:"Dashboards",labelKey:"dashboards",description:"View assigned published dashboards and Power BI reports.",icon:LayoutDashboard,route:"/dashboards",status:"active",permission:"can_access_dashboards",category:"Insights"},
  {id:"admin",name:"Admin Center",shortName:"Admin Center",labelKey:"admin",description:"Manage users, access, branding, themes, and governance.",icon:ShieldCheck,route:"/admin",status:"active",permission:"can_access_admin",category:"Administration"},
];

const stockUser=["can_access_stock","can_request_stock","can_view_own_stock_requests","can_access_stock_categories"];
const inventoryUser=["can_access_inventory","can_view_own_assets"];
const inventoryManager=["can_manage_inventory","can_export_inventory","can_import_inventory","can_export_asset_form"];
const stockManager=["can_manage_stock","can_import_stock","can_approve_stock_requests","can_export_stock","can_view_all_stock_requests","can_manage_stock_requests","can_manage_stock_categories","can_access_stock_cards","can_manage_stock_cards","can_export_stock_cards","can_export_stock_card","can_export_stock_movements","can_export_annual_stock_summary"];
const adminManager=["can_manage_users","can_manage_permissions","can_manage_organization_branding","can_manage_themes","can_manage_dashboards","can_view_all_dashboards"];
const signUser=["can_access_sign","can_sign_documents","can_view_own_signature_requests","can_download_signed_documents","can_verify_signed_documents","can_upload_own_signature"];
const signManager=["can_create_signature_envelope","can_send_signature_envelope","can_cancel_signature_envelope","can_view_all_signature_envelopes","can_manage_sign_settings","can_manage_user_signatures"];
const lanUser=["can_access_lan_messenger","can_send_lan_messages","can_create_lan_groups","can_create_lan_channels","can_upload_lan_attachments","can_schedule_lan_meetings","can_join_lan_meetings","can_start_lan_voice_call","can_start_lan_video_call","can_start_lan_group_voice_call","can_start_lan_group_video_call"];
const lanManager=["can_manage_lan_groups","can_manage_lan_channels","can_manage_lan_meetings","can_manage_lan_messenger_settings"];
const roleFallback={
  user:["can_access_workspace","can_access_helpdesk","can_access_dashboards",...inventoryUser,...stockUser,...signUser,...lanUser],
  support:["can_access_workspace","can_access_helpdesk","can_access_knowledge","can_access_tasks","can_access_dashboards",...signUser,...lanUser],
  manager:["can_access_workspace","can_access_helpdesk","can_access_tasks","can_access_reports","can_access_dashboards",...stockUser,...signUser,...lanUser],
  inventory_officer:["can_access_workspace","can_access_dashboards",...inventoryUser,...inventoryManager,...stockUser,...stockManager,...signUser,"can_create_signature_envelope","can_send_signature_envelope",...lanUser],
  stock_manager:["can_access_workspace","can_access_dashboards",...stockUser,...stockManager,...signUser],
  admin:["can_access_workspace",...moduleRegistry.map(module=>module.permission),...inventoryUser,...inventoryManager,...stockUser,...stockManager,...adminManager,...signUser,...signManager,...lanUser,...lanManager],
  super_admin:["can_access_workspace",...moduleRegistry.map(module=>module.permission),...inventoryUser,...inventoryManager,...stockUser,...stockManager,...adminManager,...signUser,...signManager,...lanUser,...lanManager],
};

export function permissionsFor(user){return new Set(user?.permissions?.length?user.permissions:roleFallback[user?.role]||[]);}
export function canAccess(user,permission){return permissionsFor(user).has(permission);}
export function accessibleModules(user){const permissions=permissionsFor(user);return moduleRegistry.filter(module=>module.status!=="hidden"&&permissions.has(module.permission));}
export function moduleById(id){return moduleRegistry.find(module=>module.id===id);}
