import {
  CalendarPlus, Download, FileUp, Hash, MessageCircle, Mic, Phone, PhoneOff, Plus,
  Search, Send, Users, Video, X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, downloadProtected } from "../api";
import { useAuth } from "../auth";
import UserAvatar from "../components/UserAvatar";

const emptyMeeting = { title: "", description: "", meeting_type: "video", conversation_id: "", participant_ids: [], start_time: "", end_time: "" };

export default function LanMessenger() {
  const { user } = useAuth();
  const location = useLocation();
  const [conversations, setConversations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);
  const [meetings, setMeetings] = useState([]);
  const [messagePage, setMessagePage] = useState(1);
  const [messagePages, setMessagePages] = useState(1);
  const [users, setUsers] = useState([]);
  const [mode, setMode] = useState("messages");
  const [conversationQuery, setConversationQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [messageError, setMessageError] = useState("");
  const [composer, setComposer] = useState("");
  const [create, setCreate] = useState(null);
  const [meeting, setMeeting] = useState(null);
  const [activeCall, setActiveCall] = useState(null);
  const [callWindow, setCallWindow] = useState(false);
  const fileRef = useRef(null);
  const messagesRef = useRef(null);
  const loadingOlderRef = useRef(false);

  function friendlyError(err) {
    if (err?.message === "Failed to fetch" || err?.message?.includes("Backend is not reachable")) {
      return "The chat service is not reachable right now. Please make sure the backend is running on port 8000, then retry.";
    }
    return err?.message || "Something went wrong";
  }

  async function loadConversations({ silent = false } = {}) {
    try {
      const rows = await api("/lan-messenger/conversations");
      setConversations(Array.isArray(rows) ? rows : []);
      if (selected) {
        const fresh = (Array.isArray(rows) ? rows : []).find((row) => row.id === selected.id);
        if (fresh) setSelected(fresh);
      }
      if (!silent) setError("");
    } catch (err) {
      if (!silent) setError(friendlyError(err));
    } finally {
      setLoading(false);
    }
  }

  async function loadMessages(id = selected?.id, page = 1, { initial = false, older = false, silent = false } = {}) {
    if (!id) return;
    const history = messagesRef.current;
    const previousHeight = history?.scrollHeight || 0;
    const stickToBottom = initial || !history || history.scrollHeight - history.scrollTop - history.clientHeight < 90;
    try {
      const data = await api(`/lan-messenger/conversations/${id}/messages?page=${page}&page_size=50`);
      const items = Array.isArray(data.items) ? data.items : [];
      setMessagePages(data.pages || data.total_pages || 1);
      if (older) {
        setMessages((current) => {
          const known = new Set(current.map((item) => item.id));
          return [...items.filter((item) => !known.has(item.id)), ...current];
        });
        setMessagePage(page);
        setTimeout(() => {
          const box = messagesRef.current;
          if (box) box.scrollTop = box.scrollHeight - previousHeight;
        }, 20);
      } else {
        setMessages((current) => {
          const rows = new Map(current.map((item) => [item.id, item]));
          items.forEach((item) => rows.set(item.id, item));
          return [...rows.values()].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
        });
        if (stickToBottom) {
          setTimeout(() => {
            const box = messagesRef.current;
            if (box) box.scrollTop = box.scrollHeight;
          }, 20);
        }
      }
      setMessageError("");
    } catch (err) {
      if (!silent) setMessageError(friendlyError(err));
    }
  }

  async function loadOlderMessages(event) {
    if (event.currentTarget.scrollTop > 28 || messagePage >= messagePages || loadingOlderRef.current || !selected) return;
    loadingOlderRef.current = true;
    try {
      await loadMessages(selected.id, messagePage + 1, { older: true });
    } finally {
      loadingOlderRef.current = false;
    }
  }

  async function loadMeetings() {
    try { setMeetings(await api("/lan-messenger/meetings")); }
    catch (err) { setError(friendlyError(err)); }
  }

  useEffect(() => {
    loadConversations();
    api("/lan-messenger/users").then((rows) => setUsers(Array.isArray(rows) ? rows : [])).catch(() => {});
    api("/lan-messenger/calls/active").then((rows) => setActiveCall(rows[0] || null)).catch(() => {});
  }, []);
  useEffect(() => { if (mode === "meetings") loadMeetings(); }, [mode]);
  useEffect(() => {
    if (!selected || mode !== "messages") return;
    setMessages([]);
    setMessageError("");
    setMessagePage(1);
    setMessagePages(1);
    loadMessages(selected.id, 1, { initial: true });
    const timer = setInterval(() => loadMessages(selected.id, 1, { silent: true }), 4000);
    return () => clearInterval(timer);
  }, [selected?.id, mode]);

  async function submitMessage(event) {
    event.preventDefault();
    if (!composer.trim() || !selected) return;
    try {
      await api(`/lan-messenger/conversations/${selected.id}/messages`, { method: "POST", body: JSON.stringify({ content: composer.trim() }) });
      setComposer("");
      loadMessages(selected.id, 1, { silent: true });
      loadConversations({ silent: true });
    } catch (err) {
      setError(friendlyError(err));
    }
  }

  async function createConversation(event) {
    event.preventDefault();
    try {
      const saved = await api("/lan-messenger/conversations", { method: "POST", body: JSON.stringify(create) });
      setCreate(null);
      await loadConversations();
      setSelected(saved);
      setMode("messages");
    } catch (err) {
      setError(friendlyError(err));
    }
  }

  async function uploadFile(event) {
    const file = event.target.files[0];
    if (!file || !selected) return;
    try {
      const seed = await api(`/lan-messenger/conversations/${selected.id}/messages`, { method: "POST", body: JSON.stringify({ content: `Shared ${file.name}` }) });
      const body = new FormData();
      body.append("file", file);
      await api(`/lan-messenger/messages/${seed.id}/attachments`, { method: "POST", body });
      loadMessages(selected.id, 1, { silent: true });
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      event.target.value = "";
    }
  }

  async function scheduleMeeting(event) {
    event.preventDefault();
    try {
      await api("/lan-messenger/meetings", {
        method: "POST",
        body: JSON.stringify({
          ...meeting,
          conversation_id: meeting.conversation_id ? Number(meeting.conversation_id) : null,
          start_time: new Date(meeting.start_time).toISOString(),
          end_time: new Date(meeting.end_time).toISOString(),
        }),
      });
      setMeeting(null);
      loadMeetings();
    } catch (err) {
      setError(friendlyError(err));
    }
  }

  async function startCall(callType, target = selected) {
    if (!target) return;
    try {
      const call = await api(`/lan-messenger/conversations/${target.id}/calls`, { method: "POST", body: JSON.stringify({ call_type: callType }) });
      setActiveCall(call);
      setCallWindow(true);
      loadMessages(target.id, 1, { silent: true });
    } catch (err) {
      setError(friendlyError(err));
    }
  }

  async function joinCall() {
    try { setActiveCall(await api(`/lan-messenger/calls/${activeCall.id}/join`, { method: "POST" })); setCallWindow(true); }
    catch (err) { setError(friendlyError(err)); }
  }
  async function leaveCall() {
    try { await api(`/lan-messenger/calls/${activeCall.id}/leave`, { method: "POST" }); setActiveCall(null); setCallWindow(false); }
    catch (err) { setError(friendlyError(err)); }
  }
  async function endCall() {
    try { await api(`/lan-messenger/calls/${activeCall.id}/end`, { method: "PUT" }); setActiveCall(null); setCallWindow(false); if (selected) loadMessages(selected.id, 1, { silent: true }); }
    catch (err) { setError(friendlyError(err)); }
  }

  const grouped = useMemo(() => {
    const q = conversationQuery.trim().toLowerCase();
    const visible = conversations.filter((row) => !q || `${row.name || ""} ${(row.members || []).map((member) => member.full_name).join(" ")}`.toLowerCase().includes(q));
    return { direct: visible.filter((x) => x.type === "direct"), group: visible.filter((x) => x.type === "group"), channel: visible.filter((x) => x.type === "channel") };
  }, [conversations, conversationQuery]);
  const messageQuery = new URLSearchParams(location.search).get("q")?.trim().toLowerCase() || "";
  const visibleMessages = useMemo(() => messageQuery ? messages.filter((row) => `${row.sender_name} ${row.content}`.toLowerCase().includes(messageQuery)) : messages, [messages, messageQuery]);

  return (
    <div className="lan-page">
      <div className="pagehead lan-pagehead">
        <div><span className="eyebrow">Internal communication</span><h1>LAN Messenger</h1></div>
        <div className="actions">
          <button className="secondary" onClick={() => setMode(mode === "meetings" ? "messages" : "meetings")}><CalendarPlus />Meetings</button>
          <button className="secondary" onClick={() => setCreate({ type: "group", name: "", description: "", is_private: true, member_ids: [] })}><Users />Create Group</button>
          <button className="primary" onClick={() => setCreate({ type: "direct", name: "", description: "", is_private: true, member_ids: [] })}><Plus />New Chat</button>
        </div>
      </div>
      {error && <div className="alert error">{error}<button onClick={() => setError("")}><X /></button></div>}
      {mode === "meetings"
        ? <Meetings meetings={meetings} onCreate={() => setMeeting({ ...emptyMeeting, conversation_id: selected?.id || "" })} onJoin={async (row) => { try { await api(`/lan-messenger/meetings/${row.id}/join`, { method: "POST" }); loadMeetings(); } catch (err) { setError(friendlyError(err)); } }} />
        : <div className="lan-shell">
          <aside className="panel lan-conversations">
            <div className="lan-conversation-search"><Search /><input placeholder="Search conversations" value={conversationQuery} onChange={(e) => setConversationQuery(e.target.value)} /></div>
            {loading ? <div className="loading"><i />Loading...</div> : <>
              {[["direct", "Direct Messages", MessageCircle], ["group", "Groups", Users], ["channel", "Channels", Hash]].map(([key, title, Icon]) => (
                <section key={key}>
                  <h3><Icon />{title}</h3>
                  {grouped[key].length ? grouped[key].map((row) => {
                    const members = row.members || [];
                    const other = members.find((x) => x.user_id !== user.id);
                    return (
                      <button className={selected?.id === row.id ? "active" : ""} key={row.id} onClick={() => setSelected(row)}>
                        <UserAvatar user={row.type === "direct" ? other : { id: row.id, full_name: row.name }} className="small" />
                        <span><strong>{row.name || other?.full_name || "Conversation"}</strong><small>{row.type === "direct" ? other?.email : `${members.length} members`}</small></span>
                      </button>
                    );
                  }) : <small className="empty-line">No {title.toLowerCase()}</small>}
                </section>
              ))}
            </>}
          </aside>
          <main className="panel lan-thread">
            {!selected ? <div className="empty"><MessageCircle /><h3>Select a conversation or start a new one</h3><p>Your messages load only after you choose a conversation.</p></div> : <>
              <header>
                <div className="lan-conversation-title">
                  {selected.type === "direct" && <UserAvatar user={(selected.members || []).find((x) => x.user_id !== user.id)} className="small" />}
                  <div><h2>{selected.name || (selected.members || []).find((x) => x.user_id !== user.id)?.full_name}</h2><p>{selected.type === "direct" ? (selected.members || []).find((x) => x.user_id !== user.id)?.email : `${(selected.members || []).length} members`}</p></div>
                </div>
                <div className="actions"><button className="icon" title="Voice call" onClick={() => startCall("voice")}><Phone /></button><button className="icon" title="Video call" onClick={() => startCall("video")}><Video /></button></div>
              </header>
              <div className="lan-messages" ref={messagesRef} onScroll={loadOlderMessages}>
                {messageQuery && <div className="lan-search-result">{visibleMessages.length} message{visibleMessages.length === 1 ? "" : "s"} matching "{messageQuery}"</div>}
                {messageError && <div className="lan-inline-error"><span>{messageError}</span><button type="button" onClick={() => loadMessages(selected.id, 1, { initial: true })}>Retry</button></div>}
                {messagePage < messagePages && <div className="lan-history-hint">Scroll up for earlier messages</div>}
                {messages.length === 0 && <div className="lan-empty-messages"><MessageCircle /><strong>No messages yet</strong><span>Start the conversation.</span></div>}
                {messages.length > 0 && visibleMessages.length === 0 && <div className="lan-empty-messages"><Search /><strong>No matching messages</strong><span>Try another search.</span></div>}
                {visibleMessages.map((row) => (
                  <article className={row.sender_id === user.id ? "mine" : ""} key={row.id}>
                    <UserAvatar user={{ id: row.sender_id, full_name: row.sender_name, profile_picture_url: row.sender_profile_picture_url }} className="message-avatar" />
                    <div>
                      <strong>{row.sender_name}</strong>
                      <p>{row.is_deleted ? "Message deleted" : row.content}</p>
                      {(row.attachments || []).map((file) => <button className="attachment-chip" key={file.id} onClick={() => downloadProtected(`/lan-messenger/attachments/${file.id}/download`, file.original_filename)}><Download />{file.original_filename}</button>)}
                      <time>{new Date(row.created_at).toLocaleString()}{row.is_edited ? " · edited" : ""}</time>
                    </div>
                  </article>
                ))}
              </div>
              <form className="lan-composer" onSubmit={submitMessage}>
                <button type="button" className="icon" onClick={() => fileRef.current?.click()}><FileUp /></button>
                <input ref={fileRef} hidden type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.png,.jpg,.jpeg,.webp" onChange={uploadFile} />
                <input placeholder="Write a message..." value={composer} onChange={(e) => setComposer(e.target.value)} />
                <button className="primary"><Send /></button>
              </form>
            </>}
          </main>
        </div>}
      {create && <ConversationModal value={create} setValue={setCreate} users={users} onSubmit={createConversation} />}
      {meeting && <MeetingModal value={meeting} setValue={setMeeting} conversations={conversations} users={users} onSubmit={scheduleMeeting} />}
      {activeCall && callWindow && <CallWindow call={activeCall} user={user} onJoin={joinCall} onLeave={leaveCall} onEnd={endCall} onClose={() => setCallWindow(false)} />}
    </div>
  );
}

function CallWindow({ call, user, onJoin, onLeave, onEnd, onClose }) {
  const joined = call.participants.some((item) => item.user_id === user.id && item.status === "joined");
  return (
    <div className="lan-call-overlay">
      <section className="lan-call-window" role="dialog" aria-modal="true" aria-label={`${call.call_type} call`}>
        <header><div><span>{call.call_type === "video" ? "Video call" : "Voice call"}</span><strong>{call.call_scope} conversation</strong></div><button className="icon" onClick={onClose} title="Minimize call"><X /></button></header>
        <div className="lan-call-stage">
          <div className="call-focus-avatar">{call.call_type === "video" ? <Video /> : <Phone />}</div>
          <h2>{joined ? "You are in the call" : "Call in progress"}</h2>
          <p>{call.participants.filter((item) => item.status === "joined").length} joined · {call.participants.length} invited</p>
          <div className="call-participants">{call.participants.map((person) => <article key={person.user_id} className={person.status}><UserAvatar user={person} className="small" /><strong>{person.full_name}</strong><small>{person.status}</small></article>)}</div>
        </div>
        <footer><button className="call-control" title="Microphone status"><Mic /></button>{call.call_type === "video" && <button className="call-control" title="Camera status"><Video /></button>}{!joined && <button className="primary" onClick={onJoin}>Join call</button>}{joined && <button className="call-control danger" onClick={onLeave} title="Leave call"><PhoneOff /></button>}{call.started_by_id === user.id && <button className="danger end-call" onClick={onEnd}>End for everyone</button>}</footer>
        <small className="call-foundation-note">Call session management is active. Full voice/video media transport requires the planned WebRTC deployment.</small>
      </section>
    </div>
  );
}

function ConversationModal({ value, setValue, users, onSubmit }) {
  return <div className="modal-backdrop"><form className="modal-card wide-modal" onSubmit={onSubmit}><div className="panel-title"><h2>New conversation</h2><button type="button" className="icon" onClick={() => setValue(null)}><X /></button></div><label>Type<select value={value.type} onChange={(e) => setValue({ ...value, type: e.target.value, member_ids: [] })}><option value="direct">Direct message</option><option value="group">Group</option><option value="channel">Channel</option></select></label>{value.type !== "direct" && <><label>Name<input required value={value.name} onChange={(e) => setValue({ ...value, name: e.target.value })} /></label><label>Description<textarea value={value.description} onChange={(e) => setValue({ ...value, description: e.target.value })} /></label></>}<fieldset><legend>{value.type === "direct" ? "Choose one user" : "Choose members"}</legend><div className="lan-user-picker">{users.map((person) => <label key={person.id}><input type={value.type === "direct" ? "radio" : "checkbox"} checked={value.member_ids.includes(person.id)} onChange={() => setValue({ ...value, member_ids: value.type === "direct" ? [person.id] : value.member_ids.includes(person.id) ? value.member_ids.filter((id) => id !== person.id) : [...value.member_ids, person.id] })} /><span>{person.full_name}<small>{person.email}</small></span></label>)}</div></fieldset><button className="primary">Create</button></form></div>;
}

function Meetings({ meetings, onCreate, onJoin }) {
  return <section><div className="section-title"><div><h2>Meetings</h2><p>Upcoming and past internal meetings.</p></div><button className="primary" onClick={onCreate}><CalendarPlus />Schedule meeting</button></div><div className="settings-grid">{meetings.map((row) => <article className="panel meeting-card" key={row.id}><span className={`badge ${row.status}`}>{row.status}</span><h3>{row.title}</h3><p>{row.description}</p><small>{new Date(row.start_time).toLocaleString()} - {new Date(row.end_time).toLocaleString()}</small><button className="secondary" disabled={row.status === "cancelled"} onClick={() => onJoin(row)}>Join meeting</button></article>)}</div></section>;
}

function MeetingModal({ value, setValue, conversations, users, onSubmit }) {
  return <div className="modal-backdrop"><form className="modal-card wide-modal" onSubmit={onSubmit}><div className="panel-title"><h2>Schedule meeting</h2><button type="button" className="icon" onClick={() => setValue(null)}><X /></button></div><div className="grid two"><label>Title<input required value={value.title} onChange={(e) => setValue({ ...value, title: e.target.value })} /></label><label>Type<select value={value.meeting_type} onChange={(e) => setValue({ ...value, meeting_type: e.target.value })}><option>voice</option><option>video</option><option>in_person</option><option>hybrid</option></select></label><label>Start<input required type="datetime-local" value={value.start_time} onChange={(e) => setValue({ ...value, start_time: e.target.value })} /></label><label>End<input required type="datetime-local" value={value.end_time} onChange={(e) => setValue({ ...value, end_time: e.target.value })} /></label></div><label>Conversation<select value={value.conversation_id} onChange={(e) => setValue({ ...value, conversation_id: e.target.value })}><option value="">No conversation</option>{conversations.map((row) => <option key={row.id} value={row.id}>{row.name || `Conversation ${row.id}`}</option>)}</select></label><label>Agenda<textarea value={value.description} onChange={(e) => setValue({ ...value, description: e.target.value })} /></label><div className="lan-user-picker">{users.map((person) => <label key={person.id}><input type="checkbox" checked={value.participant_ids.includes(person.id)} onChange={() => setValue({ ...value, participant_ids: value.participant_ids.includes(person.id) ? value.participant_ids.filter((id) => id !== person.id) : [...value.participant_ids, person.id] })} />{person.full_name}</label>)}</div><button className="primary">Schedule</button></form></div>;
}
