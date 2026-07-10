import { ImagePlus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { useBranding } from "../branding";
import { useTranslation } from "../i18n";
import { themes } from "../themes";

const initial={organization_name:"",organization_short_name:"",primary_color:"#2563eb",theme_id:"faza-blue",support_email:"",address:"",footer_text:""};
export default function OrganizationBranding(){
  const {branding,refreshBranding,logoUrl,smallLogoUrl,defaultAppIcon,defaultSmallLogo}=useBranding(); const {t}=useTranslation();
  const [form,setForm]=useState(initial); const [logo,setLogo]=useState(null); const [smallLogo,setSmallLogo]=useState(null);
  const [busy,setBusy]=useState(false); const [error,setError]=useState(""); const [success,setSuccess]=useState("");
  useEffect(()=>setForm({...initial,...branding,support_email:branding.support_email||"",address:branding.address||"",footer_text:branding.footer_text||""}),[branding]);
  async function save(e){e.preventDefault();setBusy(true);setError("");setSuccess("");try{await api("/organization-settings",{method:"PUT",body:JSON.stringify(form)});if(logo){const data=new FormData();data.append("file",logo);await api("/organization-settings/logo",{method:"POST",body:data});}if(smallLogo){const data=new FormData();data.append("file",smallLogo);await api("/organization-settings/collapsed-sidebar-icon",{method:"POST",body:data});}await refreshBranding();setLogo(null);setSmallLogo(null);setSuccess("Organization branding and logo files were saved.");}catch(err){setError(err.message);}finally{setBusy(false);}}
  async function remove(kind){setBusy(true);setError("");setSuccess("");try{await api(`/organization-settings/${kind}`,{method:"DELETE"});await refreshBranding();setSuccess(kind==="logo"?"Organization logo removed.":"Collapsed sidebar icon removed.");}catch(err){setError(err.message);}finally{setBusy(false);}}
  const logoSrc=logo?URL.createObjectURL(logo):logoUrl;
  const smallSrc=smallLogo?URL.createObjectURL(smallLogo):(smallLogoUrl||defaultSmallLogo);
  return <div className="settings-page">
    <div className="pagehead"><div><span className="eyebrow">{t("admin")}</span><h1>{t("organizationBranding")}</h1><p>Customize this deployment while keeping Operations Portal as the fallback identity.</p></div></div>
    <form className="panel branding-form" onSubmit={save}>
      {error&&<div className="alert error">{error}</div>}{success&&<div className="alert success">{success}</div>}
      <div className="branding-preview">
        <div className="branding-logo-preview"><img src={logoSrc||defaultAppIcon} alt={logoSrc?"Organization logo":"Default portal icon"}/></div>
        <div><strong>{form.organization_name||"Your organization"}</strong><span>Operations Portal</span></div>
      </div>
      <div className="grid two">
        <label>Organization name<input value={form.organization_name} required onChange={e=>setForm({...form,organization_name:e.target.value})}/></label>
        <label>Short name<input value={form.organization_short_name} required onChange={e=>setForm({...form,organization_short_name:e.target.value})}/></label>
        <label>Support email<input type="email" value={form.support_email} onChange={e=>setForm({...form,support_email:e.target.value})}/></label>
        <label>Custom primary color<input type="color" value={form.primary_color} onChange={e=>setForm({...form,primary_color:e.target.value})}/></label>
      </div>
      <div><span className="eyebrow">Workspace theme</span><h2>Choose a professional theme</h2><div className="theme-grid">{themes.map(theme=><button type="button" key={theme.id} className={`theme-card ${form.theme_id===theme.id?"selected":""}`} onClick={()=>setForm({...form,theme_id:theme.id,primary_color:theme.primary})}><span className="theme-swatch" style={{background:theme.sidebar}}><i style={{background:theme.primary}}/><b style={{background:theme.accent}}/></span><strong>{theme.name}</strong><small>{theme.primary}</small></button>)}</div></div>
      <label>Address or note<textarea rows="2" value={form.address} onChange={e=>setForm({...form,address:e.target.value})}/></label>
      <label>Footer text<input value={form.footer_text} onChange={e=>setForm({...form,footer_text:e.target.value})}/></label>
      <div className="grid two logo-inputs">
        <div><h3>{t("organizationLogo")}</h3>{logoSrc&&<img src={logoSrc} alt="" className="upload-preview"/>}<label className="secondary file-button"><ImagePlus size={16}/>Choose main logo<input type="file" accept=".jpg,.jpeg,.png,.webp" onChange={e=>setLogo(e.target.files[0]||null)}/></label>{branding.logo_url&&<button type="button" className="ghost danger" onClick={()=>remove("logo")}><Trash2 size={14}/>Remove</button>}</div>
        <div><h3>Collapsed sidebar icon</h3>{smallSrc&&<img src={smallSrc} alt="Collapsed sidebar icon" className="upload-preview small"/>}<label className="secondary file-button"><ImagePlus size={16}/>Choose sidebar icon<input type="file" accept=".jpg,.jpeg,.png,.webp" onChange={e=>setSmallLogo(e.target.files[0]||null)}/></label>{(branding.collapsed_sidebar_icon_url||branding.small_logo_url)&&<button type="button" className="ghost danger" onClick={()=>remove("collapsed-sidebar-icon")}><Trash2 size={14}/>Remove</button>}</div>
      </div>
      <div className="form-actions"><button className="primary" disabled={busy}>{busy?t("loading"):t("save")}</button></div>
    </form>
  </div>;
}
