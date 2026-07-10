import { Archive, Bell, CheckSquare, MoreVertical, Palette, Pin, Plus, Search, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";

const colors = ["#ffffff", "#f8b4b4", "#fed7aa", "#fef3c7", "#dcfce7", "#ccfbf1", "#dbeafe", "#e9d5ff", "#fce7f3"];
const blank = { title: "", body: "", checklist: [""], color: "#ffffff", reminder_at: "", is_checklist: false };

export default function Tasks() {
  const { user } = useAuth();
  const storageKey = `operations-tasks-${user.id}`;
  const [notes, setNotes] = useState(() => {
    try { return JSON.parse(localStorage.getItem(storageKey) || "[]"); } catch { return []; }
  });
  const [draft, setDraft] = useState(blank);
  const [query, setQuery] = useState("");
  const [view, setView] = useState("notes");
  const [expanded, setExpanded] = useState(false);

  useEffect(() => { localStorage.setItem(storageKey, JSON.stringify(notes)); }, [notes, storageKey]);

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    return notes
      .filter((note) => view === "trash" ? note.deleted_at : view === "archive" ? note.archived : !note.deleted_at && !note.archived)
      .filter((note) => !term || `${note.title} ${note.body} ${note.checklist?.join(" ")}`.toLowerCase().includes(term))
      .sort((a, b) => Number(Boolean(b.pinned)) - Number(Boolean(a.pinned)) || new Date(b.updated_at) - new Date(a.updated_at));
  }, [notes, query, view]);

  function saveDraft() {
    const hasChecklist = draft.is_checklist && draft.checklist.some((item) => item.trim());
    if (!draft.title.trim() && !draft.body.trim() && !hasChecklist) {
      setExpanded(false);
      setDraft(blank);
      return;
    }
    const now = new Date().toISOString();
    setNotes((current) => [{
      ...draft,
      id: crypto.randomUUID(),
      checklist: draft.checklist.filter((item) => item.trim()),
      created_at: now,
      updated_at: now,
      pinned: false,
      archived: false,
      deleted_at: null,
    }, ...current]);
    setDraft(blank);
    setExpanded(false);
  }

  function updateNote(id, changes) {
    setNotes((current) => current.map((note) => note.id === id ? { ...note, ...changes, updated_at: new Date().toISOString() } : note));
  }

  function removeForever(id) {
    setNotes((current) => current.filter((note) => note.id !== id));
  }

  return <div className="tasks-page keep-style">
    <div className="keep-topbar">
      <div><h1>Tasks</h1><p>Quick notes, checklists, reminders, and operational follow-ups.</p></div>
      <label className="keep-search"><Search size={18}/><input placeholder="Search tasks and notes" value={query} onChange={(e) => setQuery(e.target.value)}/></label>
    </div>
    <aside className="keep-sidebar">
      <button className={view === "notes" ? "active" : ""} onClick={() => setView("notes")}><Pin/>Notes</button>
      <button className={view === "archive" ? "active" : ""} onClick={() => setView("archive")}><Archive/>Archive</button>
      <button className={view === "trash" ? "active" : ""} onClick={() => setView("trash")}><Trash2/>Trash</button>
    </aside>
    <main className="keep-main">
      <section className={`keep-composer ${expanded ? "expanded" : ""}`} style={{ background: draft.color }}>
        {!expanded ? <button className="keep-take-note" onClick={() => setExpanded(true)}>Take a note...</button> : <>
          <input className="keep-title-input" placeholder="Title" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}/>
          {draft.is_checklist ? <div className="keep-checklist-editor">
            {draft.checklist.map((item, index) => <label key={index}><CheckSquare size={17}/><input placeholder="List item" value={item} onChange={(e) => setDraft({ ...draft, checklist: draft.checklist.map((row, i) => i === index ? e.target.value : row) })}/></label>)}
            <button onClick={() => setDraft({ ...draft, checklist: [...draft.checklist, ""] })}><Plus size={17}/>List item</button>
          </div> : <textarea rows="3" placeholder="Write a task, reminder, or note..." value={draft.body} onChange={(e) => setDraft({ ...draft, body: e.target.value })}/>}
          <div className="keep-toolbar">
            <button title="Checklist" onClick={() => setDraft({ ...draft, is_checklist: !draft.is_checklist })}><CheckSquare/></button>
            <label title="Reminder"><Bell/><input type="datetime-local" value={draft.reminder_at} onChange={(e) => setDraft({ ...draft, reminder_at: e.target.value })}/></label>
            <div className="keep-color-menu"><Palette/>{colors.map((color) => <button key={color} style={{ background: color }} className={draft.color === color ? "selected" : ""} onClick={() => setDraft({ ...draft, color })}/>)}</div>
            <button className="ghost" onClick={() => { setDraft(blank); setExpanded(false); }}><X size={16}/>Close</button>
            <button className="primary" onClick={saveDraft}>Save</button>
          </div>
        </>}
      </section>
      {visible.length === 0 ? <div className="keep-empty"><Pin/><h2>Notes you add appear here</h2><p>Use colors, reminders, archive, and trash to organize your work.</p></div> : <section className="keep-grid">
        {visible.map((note) => <article className="keep-note" key={note.id} style={{ background: note.color }}>
          <div className="keep-note-head"><h3>{note.title || "Untitled"}</h3>{!note.deleted_at && <button onClick={() => updateNote(note.id, { pinned: !note.pinned })}><Pin className={note.pinned ? "active-pin" : ""}/></button>}</div>
          {note.is_checklist ? <ul>{note.checklist.map((item, index) => <li key={index}><CheckSquare size={15}/>{item}</li>)}</ul> : <p>{note.body}</p>}
          {note.reminder_at && <small><Bell size={13}/>Reminder: {new Date(note.reminder_at).toLocaleString()}</small>}
          <footer>
            {note.deleted_at ? <button onClick={() => removeForever(note.id)}><Trash2/>Delete forever</button> : <>
              <button onClick={() => updateNote(note.id, { archived: !note.archived })}><Archive/>{note.archived ? "Unarchive" : "Archive"}</button>
              <button onClick={() => updateNote(note.id, { deleted_at: new Date().toISOString() })}><Trash2/>Trash</button>
            </>}
            <MoreVertical/>
          </footer>
        </article>)}
      </section>}
      <p className="keep-reminder-note">Email reminders are prepared in the UI. SMTP delivery can be connected in a later backend pass.</p>
    </main>
  </div>;
}
