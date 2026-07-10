import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, apiUrl } from "./api";
import { themeById } from "./themes";

const defaults={organization_name:"Mission Operations Portal",organization_short_name:"Operations Portal",primary_color:"#2563eb",theme_id:"operations-blue",logo_url:null,small_logo_url:null,footer_text:null};
const BrandingContext=createContext({branding:defaults,refreshBranding:()=>{}});
export function BrandingProvider({children}){
  const [branding,setBranding]=useState(defaults);
  const [revision,setRevision]=useState(0);
  async function refreshBranding(){
    try{setBranding({...defaults,...await api("/organization-settings")});}catch{setBranding(defaults);}
    finally{setRevision(Date.now());}
  }
  useEffect(()=>{refreshBranding();},[]);
  useEffect(()=>{
    const theme=themeById(branding.theme_id);const root=document.documentElement.style;
    root.setProperty("--brand-primary",branding.primary_color||theme.primary);
    root.setProperty("--navy",theme.sidebar);root.setProperty("--theme-topbar",theme.topbar);
    root.setProperty("--theme-active",theme.active);root.setProperty("--theme-accent",theme.accent);
    root.setProperty("--theme-background",theme.background);
  },[branding.primary_color,branding.theme_id]);
  const stamp=encodeURIComponent(`${branding.updated_at||""}-${revision}`);
  const collapsedIconPath=branding.collapsed_sidebar_icon_url||branding.small_logo_url;
  const value=useMemo(()=>({
    branding,
    refreshBranding,
    logoUrl:branding.logo_url?`${apiUrl(branding.logo_url.replace("/api",""))}?v=${stamp}`:null,
    smallLogoUrl:collapsedIconPath?`${apiUrl(collapsedIconPath.replace("/api",""))}?v=${stamp}`:null,
    defaultAppIcon:"/assets/branding/operations-portal-app-icon.png",
    defaultLogoLight:"/assets/branding/operations-portal-app-icon.png",
    defaultLogoDark:"/assets/branding/operations-portal-app-icon.png",
    defaultSmallLogo:"/assets/branding/operations-sidebar-icon.png",
  }),[branding,collapsedIconPath,stamp]);
  return <BrandingContext.Provider value={value}>{children}</BrandingContext.Provider>;
}
export const useBranding=()=>useContext(BrandingContext);

