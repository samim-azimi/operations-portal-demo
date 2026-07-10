import { ArrowRight, Bell, CalendarDays, CloudSun, PackageSearch, Search, ShoppingBasket, TicketCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Badge, ErrorBox, fmt, Loading } from "../components/UI";
import { useTranslation } from "../i18n";
import { accessibleModules } from "../modules";

export default function Workspace(){
  const {user}=useAuth();
  const {t}=useTranslation();
  const [query,setQuery]=useState("");
  const [summary,setSummary]=useState(null);
  const [error,setError]=useState("");
  const [searching,setSearching]=useState(false);
  const [searchResults,setSearchResults]=useState([]);
  const [searchError,setSearchError]=useState("");
  const [now,setNow]=useState(()=>new Date());
  const [weather,setWeather]=useState({status:"locating"});
  const modules=accessibleModules(user);

  function loadSummary(){
    setError("");
    api("/workspace/summary").then(setSummary).catch(err=>setError(err.message));
  }
  useEffect(loadSummary,[]);
  useEffect(()=>{
    const value=query.trim();
    if(value.length<2){setSearchResults([]);setSearchError("");return;}
    const timer=setTimeout(async()=>{
      setSearching(true);setSearchError("");
      try{
        const result=await api(`/workspace/search?${new URLSearchParams({q:value,limit:10})}`);
        setSearchResults(result.items||[]);
      }catch(err){setSearchError(err.message);setSearchResults([]);}
      finally{setSearching(false);}
    },250);
    return()=>clearTimeout(timer);
  },[query]);
  useEffect(()=>{const timer=setInterval(()=>setNow(new Date()),60_000);return()=>clearInterval(timer);},[]);
  useEffect(()=>{
    if(!navigator.geolocation){setWeather({status:"unavailable"});return;}
    navigator.geolocation.getCurrentPosition(async position=>{
      try{
        const params=new URLSearchParams({latitude:String(position.coords.latitude),longitude:String(position.coords.longitude),current:"temperature_2m,apparent_temperature,weather_code",timezone:"auto"});
        const response=await fetch(`https://api.open-meteo.com/v1/forecast?${params}`);
        if(!response.ok)throw new Error("Weather service unavailable");
        const data=await response.json();
        setWeather({status:"ready",temperature:data.current.temperature_2m,feels:data.current.apparent_temperature,code:data.current.weather_code,unit:data.current_units.temperature_2m});
      }catch{setWeather({status:"unavailable"});}
    },()=>setWeather({status:"permission"}),{enableHighAccuracy:false,timeout:8000,maximumAge:900000});
  },[]);
  const filtered=useMemo(()=>{
    const value=query.trim().toLowerCase();
    return modules.filter(module=>!value||`${module.name} ${module.description} ${module.category}`.toLowerCase().includes(value));
  },[modules,query]);

  if(!summary)return <div className="workspace-page">
    <ErrorBox error={error}/>
    {error?<div className="state-page"><h2>Workspace summary is unavailable</h2><p>The platform launcher could not load its summary information.</p><button className="primary" onClick={loadSummary}>Try again</button></div>:<Loading/>}
  </div>;

  return <div className="workspace-page">
    <section className="workspace-dashboard-header">
      <div><h1>{t("dashboard")}</h1><p>Access your available modules and recent activity · {summary.active_modules} active modules</p></div>
      <div className="workspace-search portal-search"><Search/><input aria-label={t("search")} placeholder="Search tickets, assets, stock requests, documents, modules..." value={query} onChange={e=>setQuery(e.target.value)}/>
        {query.trim().length>=2&&<div className="portal-search-results">
          {searching&&<span>Searching...</span>}
          {searchError&&<span className="error-text">{searchError}</span>}
          {!searching&&!searchError&&searchResults.length===0&&<span>No accessible results found.</span>}
          {searchResults.map((item,index)=><Link key={`${item.module}-${index}-${item.route}`} to={item.route} onClick={()=>setQuery("")}>
            <small>{item.module}</small><strong>{item.title}</strong><span>{item.subtitle}</span>
          </Link>)}
        </div>}
      </div>
    </section>
    <section className="dashboard-context-grid">
      <CalendarCard label="Gregorian" value={formatCalendar(now,"gregory","en-GB")}/>
      <CalendarCard label="Hijri Shamsi" value={formatCalendar(now,"persian","en")}/>
      <CalendarCard label="Hijri Qamari" value={formatCalendar(now,"islamic-umalqura","en")}/>
      <article className="context-card weather-card"><CloudSun/><div><span>Local weather</span>{weather.status==="ready"?<><strong>{Math.round(weather.temperature)}{weather.unit}</strong><small>{weatherLabel(weather.code)} · Feels {Math.round(weather.feels)}{weather.unit}</small></>:<><strong>—</strong><small>{weather.status==="permission"?"Allow location to show temperature":weather.status==="locating"?"Detecting your location…":"Weather unavailable"}</small></>}</div></article>
    </section>
    <div className="workspace-stat-grid">
      <article><PackageSearch/><div><span>Assets registered to me</span><strong>{summary.my_asset_count}</strong></div></article>
      <article><ShoppingBasket/><div><span>My stock requests</span><strong>{summary.my_stock_request_count}</strong></div></article>
      <article><TicketCheck/><div><span>Tickets I raised</span><strong>{summary.my_ticket_count}</strong><small>{summary.open_helpdesk_tickets??0} currently open</small></div></article>
      <article><Bell/><div><span>{t("notifications")}</span><strong>{summary.notification_count}</strong><small>Operational updates</small></div></article>
    </div>
    {Object.keys(summary.module_insights||{}).length>0&&<section className="workspace-section">
      <div className="section-title"><div><span className="eyebrow">Live overview</span><h2>My operational picture</h2></div><span>Permission-aware data</span></div>
      <div className="insight-grid">
        {summary.module_insights.helpdesk&&<InsightChart title="Help Desk" data={summary.module_insights.helpdesk} icon={TicketCheck}/>}
        {summary.module_insights.inventory&&<InsightChart title="IMS" data={summary.module_insights.inventory} icon={PackageSearch}/>}
        {summary.module_insights.stock&&<InsightChart title="Stock requests" data={summary.module_insights.stock} icon={ShoppingBasket}/>}
      </div>
    </section>}
    <section className="workspace-section">
      <div className="section-title"><div><span className="eyebrow">App launcher</span><h2>My accessible platforms</h2></div><span>{filtered.length} available</span></div>
      <div className="module-grid">{filtered.map(module=>{
        const Icon=module.icon;
        return <article className="module-card" key={module.id}>
          <div className={`module-icon module-${module.id}`}><Icon/></div>
          <div className="module-card-head"><span>{module.category}</span><Badge type={module.status==="active"?"resolved":"closed"}>{module.status==="active"?t("active"):t("comingSoon")}</Badge></div>
          <h3>{t(module.labelKey)}</h3>
          <p>{module.description}</p>
          <div className="module-card-footer"><span className="access-granted">{t("accessGranted")}</span><Link to={module.route}>{t("openModule")} <ArrowRight/></Link></div>
        </article>;
      })}</div>
    </section>
    <div className="workspace-lower">
      <section className="panel">
        <div className="panel-title"><div><span className="eyebrow">Across your workspace</span><h2>Recent activity</h2></div></div>
        {summary.recent_activity.length?<div className="workspace-activity">{summary.recent_activity.map(item=><Link to={`/tickets/${item.id}`} key={item.id}><span className={`activity-dot ${item.status.toLowerCase().replaceAll(" ","-")}`}/><div><strong>{item.title}</strong><span>Help Desk · {fmt(item.updated_at)}</span></div><Badge>{item.status}</Badge></Link>)}</div>:<div className="quiet-state"><TicketCheck/><p>No recent platform activity to show.</p></div>}
      </section>
      <section className="panel notification-preview">
        <div className="panel-title"><div><span className="eyebrow">Updates</span><h2>{t("notifications")}</h2></div><Bell/></div>
        <div className="quiet-state"><Bell/><p>Ticket and stock notification activity appears here as services are used.</p></div>
      </section>
    </div>
  </div>;
}

function formatCalendar(value,calendar,locale){
  try{return new Intl.DateTimeFormat(`${locale}-u-ca-${calendar}`,{weekday:"short",day:"numeric",month:"long",year:"numeric"}).format(value);}
  catch{return value.toLocaleDateString();}
}
function CalendarCard({label,value}){return <article className="context-card"><CalendarDays/><div><span>{label}</span><strong>{value}</strong><small>Current date</small></div></article>;}
function weatherLabel(code){if(code===0)return"Clear";if([1,2,3].includes(code))return"Partly cloudy";if([45,48].includes(code))return"Fog";if(code>=51&&code<=67)return"Rain";if(code>=71&&code<=77)return"Snow";if(code>=80&&code<=82)return"Showers";if(code>=95)return"Thunderstorm";return"Current conditions";}
const insightColors=["#4f6fdc","#18a58f","#e6a23c","#d75b70","#7f63c8","#63869a"];
function InsightChart({title,data,icon:Icon}){
  const entries=Object.entries(data).filter(([,count])=>count>0);const total=entries.reduce((sum,[,count])=>sum+count,0);
  let cursor=0;const segments=entries.map(([,count],index)=>{const start=cursor;cursor+=total?count/total*100:0;return `${insightColors[index%insightColors.length]} ${start}% ${cursor}%`;});
  return <article className="panel insight-card"><header><span><Icon/>{title}</span><strong>{total}</strong></header><div className="insight-body"><div className="pie-chart" style={{background:total?`conic-gradient(${segments.join(",")})`:"#e8ecf2"}}><i>{total}</i></div><div className="insight-legend">{entries.length?entries.map(([label,count],index)=><div key={label}><i style={{background:insightColors[index%insightColors.length]}}/><span>{label}</span><strong>{count}</strong></div>):<small>No activity yet</small>}</div></div></article>;
}
