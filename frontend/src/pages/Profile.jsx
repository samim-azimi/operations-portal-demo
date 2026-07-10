import { Camera, Trash2, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { useTranslation } from "../i18n";
import UserAvatar from "../components/UserAvatar";

export default function Profile(){
  const {user,refreshUser}=useAuth(); const {t}=useTranslation();
  const [file,setFile]=useState(null); const [preview,setPreview]=useState(null);
  const [busy,setBusy]=useState(false); const [message,setMessage]=useState(""); const [error,setError]=useState("");
  useEffect(()=>{if(!file){setPreview(null);return;}const url=URL.createObjectURL(file);setPreview(url);return()=>URL.revokeObjectURL(url);},[file]);
  async function upload(){setBusy(true);setError("");try{const form=new FormData();form.append("file",file);await api("/profile/picture",{method:"POST",body:form});await refreshUser();setFile(null);setMessage("Profile picture updated.");}catch(err){setError(err.message);}finally{setBusy(false);}}
  async function remove(){setBusy(true);setError("");try{await api("/profile/picture",{method:"DELETE"});await refreshUser();setMessage("Profile picture removed.");}catch(err){setError(err.message);}finally{setBusy(false);}}
  return <div className="narrow-page">
    <div className="pagehead"><div><span className="eyebrow">{t("settings")}</span><h1>{t("profile")}</h1><p>Manage your personal workspace identity.</p></div></div>
    <section className="panel profile-settings-card">
      <div className="profile-picture-editor">
        {preview?<div className="avatar profile-preview"><img src={preview} alt="Preview"/></div>:<UserAvatar user={user} className="profile-preview"/>}
        <div><h2>{user.full_name}</h2><p>{user.email}</p><span className="badge active">{user.role.replaceAll("_"," ")}</span></div>
      </div>
      {error&&<div className="alert error">{error}</div>}{message&&<div className="alert success">{message}</div>}
      <div className="profile-upload-actions">
        <label className="secondary file-button"><Camera size={16}/>{t("changePicture")}<input type="file" accept=".jpg,.jpeg,.png,.webp" onChange={(e)=>setFile(e.target.files[0]||null)}/></label>
        {file&&<button className="primary" disabled={busy} onClick={upload}>{busy?t("loading"):t("uploadPicture")}</button>}
        {user.profile_picture_url&&<button className="ghost danger" disabled={busy} onClick={remove}><Trash2 size={15}/>{t("removePicture")}</button>}
      </div>
      <p className="form-help">JPG, PNG or WEBP. Maximum 3 MB. Executable and mismatched files are rejected.</p>
      <Link className="secondary signature-profile-link" to="/profile/signature">Manage my digital signature</Link>
    </section>
  </div>;
}
