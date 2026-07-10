import { AlertTriangle, ArrowLeft, BrainCircuit, Check, Copy, Download, FileText, MessageCircle, RefreshCw, Send, ShieldCheck, Sparkles, Upload, Video } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, downloadAttachment } from "../api";
import { useAuth } from "../auth";
import { Badge, ErrorBox, fmt, Loading } from "../components/UI";

const priorities = ["Low", "Medium", "High", "Critical"];
const statuses = ["Open", "In Progress", "Waiting for User", "Resolved", "Closed"];

export default function TicketDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const employee = user.role === "user";
  const staff = ["admin", "super_admin", "support"].includes(user.role);
  const fileInput = useRef(null);
  const [ticket, setTicket] = useState(null);
  const [categories, setCategories] = useState([]);
  const [assignees, setAssignees] = useState([]);
  const [videos, setVideos] = useState([]);
  const [message, setMessage] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function load() { api(`/tickets/${id}`).then(setTicket).catch((err) => setError(err.message)); }
  useEffect(() => {
    load();
    api("/categories").then(setCategories).catch(() => {});
    api(`/videos/recommended/${id}`).then(setVideos).catch(() => {});
    if (staff) api("/users/assignees").then(setAssignees).catch(() => {});
  }, [id, staff]);

  async function patch(body) {
    setSaving(true); setError("");
    try { setTicket(await api(`/tickets/${id}`, { method: "PATCH", body: JSON.stringify(body) })); }
    catch (err) { setError(err.message); } finally { setSaving(false); }
  }
  async function sendMessage(event) {
    event.preventDefault(); if (!message.trim()) return;
    setSaving(true);
    try { await api(`/tickets/${id}/messages`, { method: "POST", body: JSON.stringify({ content: message }) }); setMessage(""); load(); }
    catch (err) { setError(err.message); } finally { setSaving(false); }
  }
  async function addNote(event) {
    event.preventDefault(); if (!note.trim()) return;
    try { await api(`/tickets/${id}/notes`, { method: "POST", body: JSON.stringify({ content: note, is_internal: true }) }); setNote(""); load(); }
    catch (err) { setError(err.message); }
  }
  async function uploadMore(event) {
    const file = event.target.files?.[0]; if (!file) return;
    setSaving(true);
    try { const body = new FormData(); body.append("file", file); await api(`/tickets/${id}/attachments`, { method: "POST", body }); load(); }
    catch (err) { setError(err.message); } finally { setSaving(false); event.target.value = ""; }
  }
  async function retriage() {
    setSaving(true);
    try { setTicket(await api(`/tickets/${id}/triage`, { method: "POST" })); }
    catch (err) { setError(err.message); } finally { setSaving(false); }
  }

  if (!ticket) return <><ErrorBox error={error}/><Loading/></>;
  const ai = ticket.ai_analysis;
  const confidence = Math.round((ai?.confidence_score || 0) * 100);

  const activity = <section className="panel activity-card prominent">
    <div className="panel-title"><div><span className="eyebrow">Ticket activity</span><h2>Current progress</h2></div><Badge>{ticket.status}</Badge></div>
    <div className="progress-strip">
      {["Open", "In Progress", "Resolved", "Closed"].map((step) => {
        const order = { Open:0, "In Progress":1, "Waiting for User":1, Resolved:2, Closed:3 };
        return <div className={(order[ticket.status] ?? 0) >= order[step] ? "complete" : ""} key={step}><i/><span>{step}</span></div>;
      })}
    </div>
    <div className="assignment-banner"><div className="avatar small">{ticket.assigned_user_name?.split(" ").map((p) => p[0]).slice(0,2).join("") || "IT"}</div>
      <div><strong>{ticket.assigned_user_name ? `${ticket.assigned_user_name} is working on this ticket` : "Awaiting individual assignment"}</strong><span>{ticket.assigned_team || "IT Support"} · Last updated {fmt(ticket.updated_at)}</span></div></div>
  </section>;

  return <div className="ticket-workspace">
    <Link className="back" to={employee ? "/my-tickets" : "/tickets"}><ArrowLeft/> Back to tickets</Link>
    <section className="ticket-overview"><div><div className="ticket-id">Ticket #{String(ticket.id).padStart(4,"0")}</div><h1>{ticket.title}</h1><p>Reported by {ticket.full_name} · {fmt(ticket.created_at)}</p></div>
      <div className="overview-signals"><Badge>{ticket.priority}</Badge><Badge>{ticket.status}</Badge>{staff && ai && <span className="ai-reviewed"><BrainCircuit/> {confidence}% analysis confidence</span>}</div></section>
    <ErrorBox error={error}/>
    {!staff && activity}
    {staff && confidence > 0 && confidence < 65 && <div className="alert warning"><AlertTriangle/>Low-confidence recommendation. A support agent should review it carefully.</div>}
    <div className="detail-grid"><div className="detail-main">
      <section className="panel"><div className="panel-title"><div><span className="eyebrow">Original report</span><h2>What the user experienced</h2></div></div>
        <p className="description">{ticket.description}</p><dl className="facts">
          <div><dt>Requested category</dt><dd>{ticket.requested_category || "None"}</dd></div><div><dt>Location</dt><dd>{ticket.location}</dd></div>
          <div><dt>Device Tag number</dt><dd>{ticket.device_name || "Not provided"}</dd></div><div><dt>User urgency</dt><dd>{ticket.urgency}</dd></div></dl>
      </section>
      <section className="panel conversation-panel"><div className="panel-title"><div><span className="eyebrow"><MessageCircle/> Shared workspace</span><h2>Ticket conversation</h2><p>Messages here are visible to the requester and support team.</p></div>
        <button className="secondary" onClick={() => fileInput.current?.click()} disabled={saving}><Upload size={15}/> Add screenshot or file</button>
        <input ref={fileInput} type="file" hidden accept=".png,.jpg,.jpeg,.webp,.pdf,.txt,.log" onChange={uploadMore}/></div>
        <div className="message-thread">
          <article className="message-item"><div className="avatar small">{ticket.full_name.split(" ").map((p) => p[0]).slice(0,2).join("")}</div><div><header><strong>{ticket.full_name}</strong><span>{fmt(ticket.created_at)}</span></header><p>{ticket.description}</p></div></article>
          {(ticket.messages || []).map((item) => <article className={`message-item ${item.author_role !== "user" ? "staff-message" : ""}`} key={item.id}><div className="avatar small">{item.author_name.split(" ").map((p) => p[0]).slice(0,2).join("")}</div><div><header><strong>{item.author_name}{item.author_role !== "user" && <Badge>Support</Badge>}</strong><span>{fmt(item.created_at)}</span></header><p>{item.content}</p></div></article>)}
        </div>
        <form className="message-compose" onSubmit={sendMessage}><textarea value={message} maxLength="5000" onChange={(e) => setMessage(e.target.value)} placeholder={staff ? "Reply to the requester or ask for more details…" : "Add more information or reply to support…"}/><button className="primary" disabled={saving || !message.trim()}><Send/> Send message</button></form>
      </section>
      <section className="panel attachment-panel"><div className="panel-title"><div><span className="eyebrow">Shared evidence</span><h2>Files and screenshots</h2></div></div>
        {ticket.attachments?.length ? <div className="attachment-list">{ticket.attachments.map((file) => <article key={file.id}><div className="file-icon"><FileText/></div><div><strong>{file.original_name}</strong><span>{(file.size_bytes/1024).toFixed(1)} KB · {file.mime_type}</span></div>
          <button className="ghost" onClick={() => downloadAttachment(ticket.id,file).catch((err) => setError(err.message))}><Download/> Download</button></article>)}</div> : <p>No files have been shared yet.</p>}
      </section>
      {videos.length > 0 && <section className="panel recommended-videos"><div className="panel-title"><div><span className="eyebrow"><Video/> Self-service</span><h2>Recommended instruction videos</h2><p>These are selected from the managed library based on this ticket.</p></div></div>
        <div className="video-recommendations">{videos.map((video) => <a href={video.url} target="_blank" rel="noreferrer" key={video.id}><Video/><div><strong>{video.title}</strong><span>{video.category} · Open instruction</span><p>{video.description}</p></div></a>)}</div></section>}
      {ai && <section className="panel ai-panel"><div className="panel-title"><div><span className="eyebrow"><Sparkles/> {staff ? `Automated support analysis · ${ai.provider}` : "Recommended next steps"}</span><h2>{ai.summary}</h2></div>{staff && <span className="confidence">{confidence}% confidence</span>}</div>
        <div className="analysis-block"><h3>Likely cause</h3><p>{ai.possible_root_cause}</p></div><div className="analysis-block"><h3>Suggested troubleshooting plan</h3><ol>{ai.troubleshooting_steps.map((step,index) => <li key={step}><span>{index+1}</span>{step}</li>)}</ol></div>
        {staff && <div className="reply"><div><h3>Reply draft</h3><button className="ghost" onClick={() => navigator.clipboard.writeText(ai.suggested_user_reply)}><Copy/> Copy</button></div><p>{ai.suggested_user_reply}</p><small><ShieldCheck/> Draft only. A person decides whether to send it.</small></div>}
      </section>}
      {staff && <section className="panel"><span className="eyebrow">Private to support</span><h2>Internal notes</h2><div className="notes">{ticket.notes.map((item) => <article key={item.id}><div className="avatar small">IT</div><div><p>{item.content}</p><span>{fmt(item.created_at)} · Internal</span></div></article>)}</div>
        <form className="note-form" onSubmit={addNote}><textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add diagnostic context or a hand-off note…"/><button className="primary"><Send/> Add note</button></form></section>}
    </div><aside>
      {staff && <section className="panel action-panel"><span className="eyebrow">Support controls</span><h2>Move this ticket forward</h2>
        <label>Assigned specialist<select value={ticket.assigned_user_id || ""} onChange={(e) => patch({assigned_user_id:e.target.value ? Number(e.target.value) : null})}><option value="">Unassigned</option>{assignees.map((person) => <option value={person.id} key={person.id}>{person.full_name} — {person.role}</option>)}</select></label>
        <label>Category<select value={ticket.category} onChange={(e) => patch({category:e.target.value})}>
          {!categories.some((item) => item.name === ticket.category) && <option>{ticket.category}</option>}
          {categories.filter((item) => item.is_active !== false).map((item) => <option key={item.id}>{item.name}</option>)}
        </select></label>
        <label>Priority<select value={ticket.priority} onChange={(e) => patch({priority:e.target.value})}>{priorities.map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>Status<select value={ticket.status} onChange={(e) => { let resolution_notes; if (["Resolved","Closed"].includes(e.target.value)) { resolution_notes=window.prompt("Add resolution notes:"); if(!resolution_notes)return; } patch({status:e.target.value,resolution_notes}); }}>{statuses.map((value) => <option key={value}>{value}</option>)}</select></label>
        {ticket.human_approval_required && <div className={ticket.human_approved ? "approval done":"approval"}><ShieldCheck/><div><strong>{ticket.human_approved ? "Recommendation approved":"Human approval required"}</strong><span>Required before resolution.</span></div>{!ticket.human_approved && <button onClick={() => patch({human_approved:true})}><Check/> Approve</button>}</div>}
        <button className="secondary" onClick={() => patch({accept_ai_recommendation:true})} disabled={saving}><Check/> Accept AI recommendation</button>
        <button className="ghost full" onClick={retriage} disabled={saving}><RefreshCw/> Run AI Triage</button>
      </section>}
      {staff && activity}
      <section className="panel mini"><span className="eyebrow">Routing</span><dl><dt>Assigned specialist</dt><dd>{ticket.assigned_user_name || "Unassigned"}</dd><dt>Recommended team</dt><dd>{ai?.recommended_team || "Not available"}</dd><dt>Approval required</dt><dd>{ticket.human_approval_required ? "Yes":"No"}</dd></dl></section>
    </aside></div>
  </div>;
}
