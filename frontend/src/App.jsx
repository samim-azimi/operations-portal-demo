import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { LanguageProvider } from "./i18n";
import { BrandingProvider } from "./branding";
import { canAccess } from "./modules";

const Layout = lazy(() => import("./components/Layout"));
const About = lazy(() => import("./pages/About"));
const AccessDenied = lazy(() => import("./pages/AccessDenied"));
const AdminCenter = lazy(() => import("./pages/AdminCenter"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const KnowledgeBase = lazy(() => import("./pages/KnowledgeBase"));
const Login = lazy(() => import("./pages/Login"));
const ModulePlaceholder = lazy(() => import("./pages/ModulePlaceholder"));
const SubmitTicket = lazy(() => import("./pages/SubmitTicket"));
const TicketDetail = lazy(() => import("./pages/TicketDetail"));
const TicketList = lazy(() => import("./pages/TicketList"));
const UserManagement = lazy(() => import("./pages/UserManagement"));
const VideoLibrary = lazy(() => import("./pages/VideoLibrary"));
const Workspace = lazy(() => import("./pages/Workspace"));
const WorkspaceSettings = lazy(() => import("./pages/WorkspaceSettings"));
const Profile = lazy(() => import("./pages/Profile"));
const OrganizationBranding = lazy(() => import("./pages/OrganizationBranding"));
const Inventory = lazy(() => import("./pages/Inventory"));
const Stock = lazy(() => import("./pages/Stock"));
const Dashboards = lazy(() => import("./pages/Dashboards"));
const Sign = lazy(() => import("./pages/Sign"));
const SignProfile = lazy(() => import("./pages/SignProfile"));
const SignSettings = lazy(() => import("./pages/SignSettings"));
const LanMessenger = lazy(() => import("./pages/LanMessenger"));
const LanMessengerSettings = lazy(() => import("./pages/LanMessengerSettings"));
const Tasks = lazy(() => import("./pages/Tasks"));

function RouteLoading() {
  return <div className="route-loading"><i/><span>Opening platform…</span></div>;
}

function defaultRoute(user) {
  if (!user) return "/login";
  return user.role === "user" ? "/my-tickets" : "/workspace";
}

function Protected({ children, roles, permission }) {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) {
    const next = `${location.pathname}${location.search}`;
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />;
  }
  const roleAllowed = !roles || user.role === "super_admin" || roles.includes(user.role);
  const permissionAllowed = !permission || canAccess(user, permission);
  if (!roleAllowed || !permissionAllowed) return <AccessDenied />;
  return children;
}

function Home() {
  const { user } = useAuth();
  return <Navigate to={defaultRoute(user)} replace />;
}

function HelpDeskHome() {
  const { user } = useAuth();
  return <Navigate to={user.role === "user" ? "/my-tickets" : "/dashboard"} replace />;
}

function AppRoutes() {
  return <Suspense fallback={<RouteLoading/>}><Routes>
    <Route path="/login" element={<Login />} />
    <Route element={<Protected><Layout /></Protected>}>
      <Route path="/workspace" element={<Protected permission="can_access_workspace"><Workspace /></Protected>} />
      <Route path="/helpdesk" element={<Protected permission="can_access_helpdesk"><HelpDeskHome /></Protected>} />
      <Route path="/submit" element={<Protected permission="can_access_helpdesk" roles={["user"]}><SubmitTicket /></Protected>} />
      <Route path="/my-tickets" element={<Protected permission="can_access_helpdesk" roles={["user"]}><TicketList mine /></Protected>} />
      <Route path="/dashboard" element={<Protected permission="can_access_helpdesk" roles={["admin","support","manager"]}><Dashboard /></Protected>} />
      <Route path="/tickets" element={<Protected permission="can_access_helpdesk" roles={["admin","support","manager"]}><TicketList /></Protected>} />
      <Route path="/tickets/:id" element={<Protected permission="can_access_helpdesk"><TicketDetail /></Protected>} />
      <Route path="/knowledge" element={<Protected permission="can_access_knowledge"><KnowledgeBase /></Protected>} />
      <Route path="/knowledge-base" element={<Navigate to="/knowledge" replace />} />
      <Route path="/videos" element={<Protected permission="can_access_helpdesk"><VideoLibrary /></Protected>} />
      <Route path="/admin" element={<Protected permission="can_access_admin"><AdminCenter /></Protected>} />
      <Route path="/settings" element={<Protected permission="can_access_admin"><WorkspaceSettings /></Protected>} />
      <Route path="/users" element={<Protected permission="can_access_admin"><UserManagement /></Protected>} />
      <Route path="/tasks" element={<Protected permission="can_access_tasks"><Tasks /></Protected>} />
      <Route path="/inventory/*" element={<Protected permission="can_access_inventory"><Inventory /></Protected>} />
      <Route path="/ims" element={<Navigate to="/inventory" replace />} />
      <Route path="/stock/*" element={<Protected permission="can_access_stock"><Stock /></Protected>} />
      <Route path="/profile" element={<Profile />} />
      <Route path="/admin/organization" element={<Protected permission="can_manage_organization_branding"><OrganizationBranding /></Protected>} />
      <Route path="/lan-messenger" element={<Protected permission="can_access_lan_messenger"><LanMessenger /></Protected>} />
      <Route path="/admin/lan-messenger" element={<Protected permission="can_manage_lan_messenger_settings"><LanMessengerSettings /></Protected>} />
      <Route path="/documents" element={<ModulePlaceholder moduleId="documents" />} />
      <Route path="/procurement" element={<ModulePlaceholder moduleId="procurement" />} />
      <Route path="/events" element={<ModulePlaceholder moduleId="calendar" />} />
      <Route path="/calendar" element={<Navigate to="/events" replace />} />
      <Route path="/reports" element={<ModulePlaceholder moduleId="reports" />} />
      <Route path="/dashboards" element={<Protected permission="can_access_dashboards"><Dashboards /></Protected>} />
      <Route path="/sign/*" element={<Protected permission="can_access_sign"><Sign /></Protected>} />
      <Route path="/profile/signature" element={<Protected permission="can_upload_own_signature"><SignProfile /></Protected>} />
      <Route path="/admin/sign/settings" element={<Protected permission="can_manage_sign_settings"><SignSettings /></Protected>} />
      <Route path="/access-denied" element={<AccessDenied />} />
      <Route path="/about" element={<About />} />
    </Route>
    <Route path="*" element={<Home />} />
  </Routes></Suspense>;
}

export default function App() {
  return <LanguageProvider><BrandingProvider><AuthProvider><AppRoutes /></AuthProvider></BrandingProvider></LanguageProvider>;
}
