import { ChevronDown, ChevronRight, Grid2X2, Info, LogOut, Menu, Moon, PanelLeftClose, PanelLeftOpen, Search, Sun, Truck, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { useBranding } from "../branding";
import { useTranslation } from "../i18n";
import { accessibleModules, canAccess } from "../modules";
import LanguageSelector from "./LanguageSelector";
import PortalAssistant from "./PortalAssistant";
import UserAvatar from "./UserAvatar";

const roleLabels={super_admin:"Super Admin",admin:"Workspace Admin",support:"IT Support",manager:"Manager",inventory_officer:"Inventory Officer",stock_manager:"Stock Manager",user:"Employee"};
const routeMatches=(module,pathname)=>(module.activeRoutes||[module.route]).some(route=>pathname===route||pathname.startsWith(`${route}/`));

export default function Layout(){
  const {user,signOut}=useAuth();
  const {branding,defaultSmallLogo}=useBranding();
  const {t,direction}=useTranslation();
  const [open,setOpen]=useState(false);
  const [collapsed,setCollapsed]=useState(()=>localStorage.getItem("faza-sidebar-collapsed")==="true");
  const [darkMode,setDarkMode]=useState(()=>localStorage.getItem("operations-portal-dark-mode")==="true");
  const [query,setQuery]=useState("");
  const location=useLocation();
  const navigate=useNavigate();
  const isLanMessenger=location.pathname.startsWith("/lan-messenger");
  const isWorkspace=location.pathname==="/workspace";
  const modules=accessibleModules(user);
  const logisticsModules=modules.filter(module=>module.sidebarGroup==="logistics").sort((a,b)=>(a.sidebarGroupOrder||0)-(b.sidebarGroupOrder||0));
  const topLevelModules=modules.filter(module=>module.sidebarGroup!=="logistics");
  const logisticsActive=logisticsModules.some(module=>routeMatches(module,location.pathname));
  const [logisticsOpen,setLogisticsOpen]=useState(()=>localStorage.getItem("operations-sidebar-logistics-open")!=="false"||logisticsActive);
  const helpDeskAccess=canAccess(user,"can_access_helpdesk");
  useEffect(()=>{
    document.documentElement.setAttribute("data-theme-mode",darkMode?"dark":"light");
    localStorage.setItem("operations-portal-dark-mode",String(darkMode));
  },[darkMode]);
  useEffect(()=>{if(logisticsActive){setLogisticsOpen(true);localStorage.setItem("operations-sidebar-logistics-open","true");}},[logisticsActive]);
  function toggleCollapsed(){setCollapsed((value)=>{localStorage.setItem("faza-sidebar-collapsed",String(!value));return !value;});}
  function toggleLogistics(){setLogisticsOpen(value=>{const next=logisticsActive?true:!value;localStorage.setItem("operations-sidebar-logistics-open",String(next));return next;});}
  function search(event){
    event.preventDefault();
    if(!query.trim())return;
    if(isLanMessenger){
      navigate(`/lan-messenger?q=${encodeURIComponent(query.trim())}`);
      return;
    }
    navigate(helpDeskAccess?`/tickets?q=${encodeURIComponent(query.trim())}`:"/workspace");
    setQuery("");
  }
  function moduleLink(module,child=false){const Icon=module.icon;return <NavLink key={module.id} title={module.name} to={module.route} onClick={()=>setOpen(false)} className={({isActive})=>`${isActive||routeMatches(module,location.pathname)?"active":""}${child?" child-link":""}`.trim()}>
    <Icon size={child?17:19}/><span>{t(module.labelKey)}</span>{module.status!=="active"&&<i className="soon-dot" title={t("comingSoon")}/>}
  </NavLink>;}
  const sidebarClass=`sidebar${open?" open":""}${collapsed?" collapsed":""}`;
  return <div className={`shell faza-shell${collapsed?" sidebar-collapsed":""}`} data-content-direction={direction}>
    {open&&<button className="sidebar-backdrop mobile" aria-label="Close menu" onClick={()=>setOpen(false)}/>}
    <aside className={sidebarClass}>
      <div className="sidebar-brand-row">
        <NavLink className="brand" to="/workspace" onClick={()=>setOpen(false)} title={branding.organization_name}>
          <img className="brand-logo" src={defaultSmallLogo} alt=""/>
          <div className="brand-copy"><strong>{branding.organization_short_name||"Operations Portal"}</strong>{branding.organization_name!=="Mission Operations Portal"&&<span>Operations Portal</span>}</div>
        </NavLink>
        <button type="button" className="icon mobile sidebar-close" onClick={()=>setOpen(false)}><X/></button>
      </div>
      <button type="button" className="sidebar-collapse" onClick={toggleCollapsed} title={collapsed?"Expand sidebar":"Collapse sidebar"}>
        {collapsed?<PanelLeftOpen size={17}/>:<><PanelLeftClose size={17}/><span>Collapse</span></>}
      </button>
      <div className="workspace-label">{t("workspace")}</div>
      <nav className="module-nav">
        <NavLink to="/workspace" title={t("workspace")} onClick={()=>setOpen(false)} className={({isActive})=>isActive?"active":""}><Grid2X2 size={19}/><span>{t("workspace")}</span></NavLink>
        {logisticsModules.length>0&&<div className={`nav-group${logisticsActive?" active":""}`}>
          <button type="button" className={`nav-group-toggle${logisticsActive?" active":""}`} onClick={toggleLogistics} title={t("logistics")} aria-expanded={logisticsOpen}>
            <Truck size={19}/><span>{t("logistics")}</span>{logisticsOpen?<ChevronDown className="nav-chevron" size={15}/>:<ChevronRight className="nav-chevron" size={15}/>}
          </button>
          {logisticsOpen&&<div className="nav-group-children">{logisticsModules.map(module=>moduleLink(module,true))}</div>}
        </div>}
        {topLevelModules.map(module=>moduleLink(module))}
        <NavLink to="/about" title={t("about")} onClick={()=>setOpen(false)} className={({isActive})=>isActive?"active":""}><Info size={19}/><span>{t("about")}</span></NavLink>
      </nav>
      <div className="profile">
        <NavLink className="profile-copy" to="/profile"><strong>{user.full_name}</strong><span>{roleLabels[user.role]||user.role}</span></NavLink>
        <button className="icon" onClick={signOut} title={t("signOut")}><LogOut size={18}/></button>
      </div>
    </aside>
    <main className={isLanMessenger?"lan-main":""}>
      <header className="topbar">
        <button className="icon mobile" onClick={()=>setOpen(true)}><Menu/></button>
        {!isWorkspace&&(isLanMessenger||helpDeskAccess&&user.role!=="user")?<form className="global-search" onSubmit={search}><Search size={17}/><input aria-label={t("search")} placeholder={isLanMessenger?t("searchMessages"):t("searchHelpdesk")} value={query} onChange={(event)=>setQuery(event.target.value)}/><kbd>Ctrl K</kbd></form>:<span className="eyebrow">Operations Portal</span>}
        <div className="top-actions">
          <button type="button" className="icon theme-toggle" title={darkMode?"Use light mode":"Use dark mode"} onClick={()=>setDarkMode(value=>!value)}>
            {darkMode?<Sun size={18}/>:<Moon size={18}/>}
          </button>
          <LanguageSelector/>
          <NavLink to="/profile" className="top-avatar" title={t("profile")}><UserAvatar user={user} className="small"/></NavLink>
        </div>
      </header>
      <div className={`content${isLanMessenger?" lan-content":""}`}><Outlet/></div>
      <footer className="app-footer"><span>{branding.footer_text||branding.organization_name}</span><span>{t("designedBy")}</span></footer>
    </main>
    {isWorkspace&&<PortalAssistant/>}
  </div>;
}
