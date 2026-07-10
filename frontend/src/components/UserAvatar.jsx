import { useEffect, useState } from "react";
import { apiBlob } from "../api";

export default function UserAvatar({user,className=""}){
  const [src,setSrc]=useState(null);
  useEffect(()=>{
    let url;
    if(user?.profile_picture_url) apiBlob(user.profile_picture_url.replace("/api","")).then((blob)=>{url=URL.createObjectURL(blob);setSrc(url);}).catch(()=>setSrc(null));
    else setSrc(null);
    return()=>url&&URL.revokeObjectURL(url);
  },[user?.id,user?.profile_picture_url]);
  const initials=user?.full_name?.split(" ").map((part)=>part[0]).slice(0,2).join("")||"?";
  return <div className={`avatar ${className}`}>{src?<img src={src} alt=""/>:initials}</div>;
}
