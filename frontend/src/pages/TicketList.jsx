import { BrainCircuit, ChevronLeft, ChevronRight, Download, Filter, Plus, Search, ShieldCheck, SlidersHorizontal, Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, downloadProtected } from "../api";
import { useAuth } from "../auth";
import { Badge, Empty, ErrorBox, fmt, Loading } from "../components/UI";
import { useTranslation } from "../i18n";

export default function TicketList({ mine = false }) {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [result, setResult] = useState(null);
  const [categories, setCategories] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState(searchParams.get("q") || "");
  const [status, setStatus] = useState("All");
  const [category, setCategory] = useState("All");
  const [focus, setFocus] = useState("all");
  const [page, setPage] = useState(1);

  useEffect(() => {
    api("/categories")
      .then((items) => setCategories(items.filter((item) => item.is_active)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ page: String(page), page_size: "10" });
      if (query.trim()) params.set("q", query.trim());
      if (status !== "All") params.set("status", status);
      if (category !== "All") params.set("category", category);
      if (focus !== "all") params.set("focus", focus);
      setLoading(true);
      setError("");
      api(`/tickets?${params}`)
        .then(setResult)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [page, query, status, category, focus]);

  function changeFilter(setter, value) {
    setter(value);
    setPage(1);
  }
  function clearFilters() {
    setQuery(""); setStatus("All"); setCategory("All"); setFocus("all"); setPage(1); setSearchParams({});
  }

  const items = result?.items || [];
  return <div className={mine ? "queue-page user-queue" : "queue-page"}>
    <div className="pagehead queue-head">
      <div><span className="eyebrow">{mine ? t("yourRequests") : "Help Desk operations"}</span>
        <h1>{mine ? t("myTickets") : "Ticket queue"}</h1>
        <p>{mine ? t("myTicketsIntro") : "Prioritized support work with server-side search and pagination."}</p></div>
      {user.role === "user" && <Link className="primary link" to="/submit"><Plus size={18}/> {t("newTicket")}</Link>}
      {!mine && <div className="head-actions">
        <button className="secondary" onClick={() => downloadProtected("/tickets/export.csv","operations-helpdesk-ticket-report.csv").catch((err) => setError(err.message))}><Download size={16}/> Export CSV</button>
        <div className="queue-health"><Sparkles size={18}/><div><span>Server filtered</span><strong>Paginated queue active</strong></div></div>
      </div>}
    </div>
    <ErrorBox error={error}/>
    {!mine && <div className="queue-focus">
      <button className={focus === "all" ? "active" : ""} onClick={() => changeFilter(setFocus,"all")}>All work</button>
      <button className={focus === "approval" ? "active" : ""} onClick={() => changeFilter(setFocus,"approval")}><ShieldCheck size={15}/> Needs approval</button>
      <button className={focus === "critical" ? "active" : ""} onClick={() => changeFilter(setFocus,"critical")}>Critical</button>
      <button className={focus === "low-confidence" ? "active" : ""} onClick={() => changeFilter(setFocus,"low-confidence")}><BrainCircuit size={15}/> Low confidence</button>
    </div>}
    <section className="panel queue-panel">
      <div className="queue-toolbar">
        <div className="queue-search"><Search size={17}/><input aria-label={t("filterTickets")} placeholder={mine ? t("filterTickets") : "Search title, user, device, or issue…"} value={query} onChange={(event) => changeFilter(setQuery,event.target.value)}/>
          {query && <button onClick={() => changeFilter(setQuery,"")} title="Clear search"><X size={15}/></button>}</div>
        <label className="inline-filter"><Filter size={15}/><select aria-label="Filter by status" value={status} onChange={(event) => changeFilter(setStatus,event.target.value)}>
          <option value="All">{t("all")}</option><option value="Open">{t("open")}</option><option value="In Progress">{t("inProgress")}</option>
          <option value="Waiting for User">{t("waiting")}</option><option value="Resolved">{t("resolved")}</option><option value="Closed">{t("closed")}</option>
        </select></label>
        <label className="inline-filter"><SlidersHorizontal size={15}/><select aria-label="Filter by category" value={category} onChange={(event) => changeFilter(setCategory,event.target.value)}>
          <option value="All">{t("all")}</option>{categories.map((item) => <option key={item.id}>{item.name}</option>)}
        </select></label>
        {(query || status !== "All" || category !== "All" || focus !== "all") && <button className="ghost" onClick={clearFilters}>Reset</button>}
      </div>
      {loading && !result ? <Loading/> : <>
        <div className="queue-result-bar"><span>Showing <strong>{items.length}</strong> of {result?.total || 0} tickets</span><span>Page {result?.page || 1} of {Math.max(result?.pages || 0,1)}</span></div>
        {items.length === 0 ? <Empty title={t("noTickets")} text={query || status !== "All" || category !== "All" || focus !== "all" ? "Try clearing one or more filters." : t("noTicketsText")}/> :
          <div className={`tablewrap smart-table ${loading ? "refreshing" : ""}`}><table><thead><tr>
            {!mine && <th>Risk</th>}<th>{mine ? t("request") : "Ticket & requester"}</th><th>{t("category")} & {t("priority")}</th>
            {!mine && <th>Confidence</th>}<th>{t("status")}</th><th>{t("owner")}</th><th>{t("created")}</th>
          </tr></thead><tbody>{items.map((ticket) => {
            const confidence = Math.round((ticket.ai_analysis?.confidence_score || 0) * 100);
            return <tr key={ticket.id}>
              {!mine && <td><div className={`risk-dot ${ticket.priority.toLowerCase()}`} title={`${ticket.priority} priority`}/></td>}
              <td><Link to={`/tickets/${ticket.id}`}><strong>{ticket.title}</strong><span>#{String(ticket.id).padStart(4,"0")} · {ticket.full_name} · {ticket.device_name || "No device tag"}</span></Link></td>
              <td><div className="classification"><Badge>{ticket.priority}</Badge><span>{ticket.category}</span>{ticket.human_approval_required && !ticket.human_approved && <ShieldCheck size={14} className="approval-mini"/>}</div></td>
              {!mine && <td><div className={`confidence-cell ${confidence < 65 ? "low" : ""}`}><div><i style={{width:`${confidence}%`}}/></div><strong>{confidence}%</strong></div></td>}
              <td><Badge>{ticket.status}</Badge></td>
              <td><div className="owner-cell"><span className="team-avatar">{(ticket.assigned_team || "UN").split(" ").map((word) => word[0]).slice(0,2).join("")}</span>{ticket.assigned_user_name || ticket.assigned_team || "Unassigned"}</div></td>
              <td>{fmt(ticket.created_at)}</td>
            </tr>;
          })}</tbody></table></div>}
        {(result?.pages || 0) > 1 && <div className="pagination"><button className="ghost" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)}><ChevronLeft/> Previous</button>
          <span>Page {page} of {result.pages}</span><button className="ghost" disabled={page >= result.pages || loading} onClick={() => setPage((value) => value + 1)}>Next <ChevronRight/></button></div>}
      </>}
    </section>
  </div>;
}

