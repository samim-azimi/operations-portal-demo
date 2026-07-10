import { createContext, useContext, useEffect, useState } from "react";
import { api, login as requestLogin } from "./api";

const AuthContext=createContext(null);
export function AuthProvider({children}){
  const [user,setUser]=useState(()=>{try{return JSON.parse(localStorage.getItem("user"))}catch{return null}});
  async function signIn(email,password){
    const data=await requestLogin(email,password);
    localStorage.setItem("token",data.access_token);
    localStorage.setItem("user",JSON.stringify(data.user));
    setUser(data.user);
  }
  function updateUser(next){
    localStorage.setItem("user",JSON.stringify(next));
    setUser(next);
  }
  async function refreshUser(){ const next=await api("/profile"); updateUser(next); return next; }
  function signOut(){
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
  }
  useEffect(()=>{if(localStorage.getItem("token"))refreshUser().catch(()=>signOut());},[]);
  return <AuthContext.Provider value={{user,signIn,signOut,updateUser,refreshUser}}>{children}</AuthContext.Provider>;
}
export const useAuth=()=>useContext(AuthContext);
