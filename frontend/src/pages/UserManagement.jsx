import { ChevronLeft, ChevronRight, Download, KeyRound, Pencil, Plus, ShieldCheck, Trash2, Upload, UserCheck, Users, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { Badge, Empty, ErrorBox, Loading } from "../components/UI";
import { useTranslation } from "../i18n";

const blank = { full_name: "", email: "", password: "", role: "user", department: "", is_active: true };

export default function UserManagement() {
  const { t } = useTranslation();
  const csvRef = useRef(null);
  const [users, setUsers] = useState(null);
  const [meta, setMeta] = useState({ total: 0, pages: 0 });
  const [page, setPage] = useState(1);
  const [form, setForm] = useState(blank);
  const [editing, setEditing] = useState(null);
  const [show, setShow] = useState(false);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [importResult, setImportResult] = useState(null);

  function load(targetPage = page) {
    setError("");
    const params = new URLSearchParams({ page: String(targetPage), page_size: "25" });
    if (query.trim()) params.set("q", query.trim());
    api(`/users?${params}`).then((data) => {
      setUsers(data.items);
      setMeta(data);
    }).catch((err) => setError(err.message));
  }
  useEffect(() => {
    const timer = window.setTimeout(() => load(page), 250);
    return () => window.clearTimeout(timer);
  }, [page, query]);

  const filtered = useMemo(() => users || [], [users]);
  const summary = {
    active: users?.filter((item) => item.is_active).length || 0,
    admins: users?.filter((item) => ["admin","super_admin"].includes(item.role)).length || 0,
    support: users?.filter((item) => item.role === "support").length || 0,
  };

  function openCreate() { setEditing(null); setForm(blank); setShow(true); }
  function openEdit(person) {
    setEditing(person);
    setForm({ full_name: person.full_name, email: person.email, password: "", role: person.role, department: person.department || "", is_active: person.is_active });
    setShow(true);
  }
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const payload = editing ? { ...form } : form;
      if (editing) delete payload.password;
      await api(editing ? `/users/${editing.id}` : "/users", { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) });
      setShow(false); load();
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  async function remove(person) {
    if (!window.confirm(`Remove ${person.full_name}? Their historical ticket records will be preserved.`)) return;
    try { await api(`/users/${person.id}`, { method: "DELETE" }); load(); } catch (err) { setError(err.message); }
  }
  async function importCsv(event) {
    const file = event.target.files?.[0]; if (!file) return;
    setBusy(true); setError(""); setImportResult(null);
    try {
      const body = new FormData(); body.append("file", file);
      const result = await api("/users/bulk-import", { method: "POST", body });
      setImportResult(result); load();
    } catch (err) { setError(err.message); } finally { setBusy(false); event.target.value = ""; }
  }
  function downloadTemplate() {
    const content = "full_name,email,department,role\nJane Doe,jane@example.com,Finance,user\nJohn Smith,john@example.com,ICT,support\n";
    const url = URL.createObjectURL(new Blob([content], { type: "text/csv" }));
    const a = document.createElement("a"); a.href = url; a.download = "employee-import-template.csv"; a.click(); URL.revokeObjectURL(url);
  }

  return <div className="users-page">
    <div className="pagehead"><div><span className="eyebrow">{t("peopleAccess")}</span><h1>{t("userManagement")}</h1>
      <p>{t("userManagementIntro")}</p></div>
      <div className="head-actions"><button className="ghost" onClick={downloadTemplate}><Download size={16}/> {t("csvTemplate")}</button>
        <button className="secondary" onClick={() => csvRef.current?.click()} disabled={busy}><Upload size={16}/> {t("importCsv")}</button>
        <input ref={csvRef} hidden type="file" accept=".csv,text/csv" onChange={importCsv}/>
        <button className="primary" onClick={openCreate}><Plus size={17}/> {t("addUser")}</button></div>
    </div>
    <ErrorBox error={error}/>
    {importResult && <section className="panel import-result"><div><ShieldCheck/><span><strong>Import completed</strong>{importResult.created} created · {importResult.skipped} skipped · {importResult.failed} failed</span></div>
      {importResult.rows.some((row) => row.temporary_password) && <details><summary>Show one-time temporary passwords</summary>
        <div className="credential-list">{importResult.rows.filter((row) => row.temporary_password).map((row) => <code key={row.email}>{row.email} — {row.temporary_password}</code>)}</div>
        <small>Copy these now and share them through a secure channel. They are not shown again.</small></details>}</section>}
    <div className="user-stats">
      <article><Users/><div><span>{t("totalPeople")}</span><strong>{meta.total}</strong></div></article>
      <article><UserCheck/><div><span>{t("activeAccounts")}</span><strong>{summary.active}</strong></div></article>
      <article><ShieldCheck/><div><span>{t("administrators")}</span><strong>{summary.admins}</strong></div></article>
      <article><KeyRound/><div><span>{t("supportAgents")}</span><strong>{summary.support}</strong></div></article>
    </div>
    {show && <div className="modal-backdrop"><form className="panel user-modal" onSubmit={submit}>
      <div className="modal-head"><div><span className="eyebrow">{editing ? "Edit account" : "New account"}</span><h2>{editing ? `Update ${editing.full_name}` : "Add an employee"}</h2><p>Use the least-privileged role the person needs.</p></div>
        <button type="button" className="icon" onClick={() => setShow(false)}><X/></button></div>
      <div className="grid two">
        <label>Full name<input value={form.full_name} onChange={(e) => setForm({...form, full_name:e.target.value})} required/></label>
        <label>Email<input type="email" value={form.email} onChange={(e) => setForm({...form, email:e.target.value})} required/></label>
        {!editing && <label>Temporary password<input type="password" minLength="12" maxLength="128" value={form.password} onChange={(e) => setForm({...form,password:e.target.value})} required/><span>At least 12 characters.</span></label>}
        <label>Department<input value={form.department} onChange={(e) => setForm({...form,department:e.target.value})}/></label>
        <label>Access role<select value={form.role} onChange={(e) => setForm({...form,role:e.target.value})}>
          <option value="user">Regular user</option><option value="support">IT support agent</option><option value="manager">Manager</option>
          <option value="inventory_officer">Inventory officer</option><option value="stock_manager">Stock manager</option><option value="admin">Workspace admin</option><option value="super_admin">Super admin</option>
        </select></label>
        {editing && <label>Account status<select value={String(form.is_active)} onChange={(e) => setForm({...form,is_active:e.target.value === "true"})}><option value="true">Active</option><option value="false">Disabled</option></select></label>}
      </div>
      <div className="modal-actions"><button type="button" className="ghost" onClick={() => setShow(false)}>Cancel</button><button className="primary" disabled={busy}>{busy ? "Saving…" : "Save account"}</button></div>
    </form></div>}
    {!users ? <Loading/> : <section className="panel people-panel">
      <div className="people-toolbar"><div><h2>{t("employeeDirectory")}</h2><span>{meta.total} workspace accounts</span></div><input placeholder={t("search")} value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }}/></div>
      {!filtered.length ? <Empty title="No people found" text="Try another name, email, or department."/> : <div className="people-list">{filtered.map((person) => <article key={person.id}>
        <div className="person-avatar">{person.full_name.split(" ").map((part) => part[0]).slice(0,2).join("")}</div>
        <div className="person-name"><strong>{person.full_name}</strong><span>{person.email}</span></div>
        <span className="person-department">{person.department || "No department"}</span><Badge>{person.role}</Badge>
        <Badge type={person.is_active ? "resolved" : "closed"}>{person.is_active ? "Active" : "Disabled"}</Badge>
        <div className="row-actions"><button className="ghost" onClick={() => openEdit(person)}><Pencil/> Edit</button><button className="danger-icon" title="Remove user" onClick={() => remove(person)}><Trash2/></button></div>
      </article>)}</div>}
      {meta.pages > 1 && <div className="pagination"><button className="ghost" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}><ChevronLeft/> Previous</button><span>Page {page} of {meta.pages}</span><button className="ghost" disabled={page >= meta.pages} onClick={() => setPage((value) => value + 1)}>Next <ChevronRight/></button></div>}
    </section>}
  </div>;
}
