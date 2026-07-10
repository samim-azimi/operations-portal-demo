import { Expand, LayoutDashboard, Pencil, Plus, ShieldAlert, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { canAccess } from "../modules";

const blank = {
  title: "",
  description: "",
  embed_url: "",
  provider: "Power BI",
  is_active: true,
  allowed_roles: ["manager"],
  user_ids: [],
};
const roles = ["user", "support", "manager", "inventory_officer", "stock_manager", "admin", "super_admin"];

export default function Dashboards() {
  const { user } = useAuth();
  const manage = canAccess(user, "can_manage_dashboards");
  const [data, setData] = useState({ items: [] });
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState(null);
  const frameWrap = useRef(null);
  const cacheKey = manage ? "operations-dashboards-admin-cache" : "operations-dashboards-my-cache";
  const grouped = useMemo(() => groupDashboards(data.items || []), [data.items]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const result = await api(manage ? "/dashboards?page=1&page_size=100" : "/dashboards/my?page=1&page_size=100");
      setData(result);
      localStorage.setItem(cacheKey, JSON.stringify(result));
      setSelected((current) => current && result.items.find((item) => item.id === current.id) || result.items.find((item) => item.is_active) || null);
    } catch (err) {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        const result = JSON.parse(cached);
        setData(result);
        setSelected((current) => current && result.items.find((item) => item.id === current.id) || result.items.find((item) => item.is_active) || null);
        setError("Live dashboard list is unavailable. Showing the last cached list from this browser.");
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [manage]);

  async function save(e) {
    e.preventDefault();
    setError("");
    try {
      await api(form.id ? `/dashboards/${form.id}` : "/dashboards", {
        method: form.id ? "PUT" : "POST",
        body: JSON.stringify(form),
      });
      setForm(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function deactivate(item) {
    await api(`/dashboards/${item.id}/deactivate`, { method: "PATCH" });
    load();
  }

  async function fullscreen() {
    try {
      await frameWrap.current?.requestFullscreen?.();
    } catch {
      setError("Fullscreen could not be opened by this browser.");
    }
  }

  return <div>
    <div className="pagehead">
      <div><span className="eyebrow">Published analytics</span><h1>Dashboards</h1><p>View the dashboards assigned to your role or account.</p></div>
      {manage && <button className="primary" onClick={() => setForm({ ...blank })}><Plus size={16}/>Add dashboard</button>}
    </div>
    {error && <div className="alert error">{error}</div>}
    {loading ? <div className="loading"><i/>Loading dashboards...</div> : data.items.length === 0 ? <div className="panel empty"><LayoutDashboard/><h3>No dashboards assigned</h3><p>Ask an administrator to grant access to a published dashboard.</p></div> : <div className="dashboard-module-grid">
      <aside className="panel dashboard-list">
        <span className="eyebrow">Dashboard folders</span>
        {Object.entries(grouped).map(([folder, items]) => <section className="dashboard-folder" key={folder}>
          <h3>{folder}</h3>
          {items.map((item) => <button className={selected?.id === item.id ? "active" : ""} key={item.id} onClick={() => setSelected(item)}>
            <LayoutDashboard/>
            <div><strong>{item.title}</strong><span>{item.provider} · {item.is_active ? "Active" : "Inactive"}</span></div>
            {manage && <Pencil onClick={(event) => { event.stopPropagation(); setForm({ ...item }); }}/>}
          </button>)}
        </section>)}
      </aside>
      <section className="panel dashboard-view" ref={frameWrap}>{selected && <>
        <div className="panel-title"><div><span className="eyebrow">{selected.provider}</span><h2>{selected.title}</h2><p>{selected.description}</p></div><button className="secondary" onClick={fullscreen}><Expand size={16}/>Fullscreen</button></div>
        {selected.embed_url.startsWith("https://") ? <iframe title={selected.title} src={selected.embed_url} allowFullScreen loading="lazy" referrerPolicy="strict-origin-when-cross-origin"/> : <div className="empty"><ShieldAlert/><h3>Invalid dashboard link</h3><p>An HTTPS public/embed URL is required.</p></div>}
      </>}</section>
    </div>}
    {form && <div className="modal-backdrop"><form className="modal-card wide-modal" onSubmit={save}>
      <div className="panel-title"><h2>{form.id ? "Edit dashboard" : "Add dashboard"}</h2><button type="button" className="icon" onClick={() => setForm(null)}><X/></button></div>
      <label>Title<input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}/></label>
      <label>Description<textarea rows="2" value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })}/></label>
      <label>HTTPS public/embed URL<input type="url" required value={form.embed_url} onChange={(e) => setForm({ ...form, embed_url: e.target.value })}/></label>
      <label>Provider<input value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })}/></label>
      <fieldset><legend>Allowed roles</legend><div className="role-checks">{roles.map((role) => <label key={role}><input type="checkbox" checked={(form.allowed_roles || []).includes(role)} onChange={(e) => setForm({ ...form, allowed_roles: e.target.checked ? [...(form.allowed_roles || []), role] : (form.allowed_roles || []).filter((value) => value !== role) })}/>{role.replaceAll("_", " ")}</label>)}</div></fieldset>
      <div className="form-actions"><button className="primary">Save dashboard</button>{form.id && form.is_active && <button type="button" className="ghost danger" onClick={() => { deactivate(form); setForm(null); }}>Deactivate</button>}</div>
    </form></div>}
  </div>;
}

function dashboardFolder(item) {
  const text = `${item.title || ""} ${item.description || ""}`.toLowerCase();
  if (text.includes("health") || text.includes("dews")) return "HEALTH";
  if (text.includes("wash") || text.includes("water") || text.includes("sanitation")) return "WASH";
  if (text.includes("meal") || text.includes("monitoring") || text.includes("evaluation")) return "MEAL";
  return "GENERAL";
}

function groupDashboards(items) {
  const order = ["MEAL", "WASH", "HEALTH", "GENERAL"];
  const grouped = {};
  for (const item of items) {
    const folder = dashboardFolder(item);
    grouped[folder] = [...(grouped[folder] || []), item];
  }
  return Object.fromEntries(order.filter((folder) => grouped[folder]?.length).map((folder) => [folder, grouped[folder]]));
}
