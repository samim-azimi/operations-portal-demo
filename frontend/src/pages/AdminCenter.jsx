import { ArrowRight, Building2, FileSignature, LayoutDashboard, MapPinned, MessagesSquare, ShieldCheck, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { canAccess } from "../modules";

export default function AdminCenter() {
  const {user}=useAuth();
  return <div>
    <div className="pagehead"><div><span className="eyebrow">Portal governance</span><h1>Admin Center</h1><p>Manage people, access, branding, dashboards, and workspace configuration.</p></div></div>
    <div className="admin-launch-grid">
      <Link className="panel admin-launch-card" to="/users"><Users/><div><h2>Users and access</h2><p>Create accounts, import employees, and assign workspace roles.</p></div><ArrowRight/></Link>
      <Link className="panel admin-launch-card" to="/settings"><MapPinned/><div><h2>Help Desk settings</h2><p>Manage request categories and support locations.</p></div><ArrowRight/></Link>
      {canAccess(user,"can_manage_organization_branding")&&<Link className="panel admin-launch-card" to="/admin/organization"><Building2/><div><h2>Organization branding</h2><p>Manage the organization name, logos, color, support address, and footer.</p></div><ArrowRight/></Link>}
      {canAccess(user,"can_manage_dashboards")&&<Link className="panel admin-launch-card" to="/dashboards"><LayoutDashboard/><div><h2>Published dashboards</h2><p>Add Power BI dashboards and assign access by role or user.</p></div><ArrowRight/></Link>}
      {canAccess(user,"can_manage_sign_settings")&&<Link className="panel admin-launch-card" to="/admin/sign/settings"><FileSignature/><div><h2>Sign settings</h2><p>Manage token expiry, signature requirements, email, and signing policy.</p></div><ArrowRight/></Link>}
      {canAccess(user,"can_manage_lan_messenger_settings")&&<Link className="panel admin-launch-card" to="/admin/lan-messenger"><MessagesSquare/><div><h2>LAN Messenger settings</h2><p>Manage LAN routing, public access, attachments, meetings, and call toggles.</p></div><ArrowRight/></Link>}
      <article className="panel admin-launch-card muted"><ShieldCheck/><div><h2>Permission policies</h2><p>Role-based module permissions are centrally defined and enforced by the API.</p></div><span className="module-status coming">Managed in code</span></article>
    </div>
  </div>;
}
