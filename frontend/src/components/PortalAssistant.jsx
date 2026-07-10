import { MessageCircle, Send, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

const suggestions = ["Create a ticket", "Show my assets", "Request stock", "Sign a document"];
const welcome = {
  role: "assistant",
  text: "Hello! I am your Portal Guide. I can help you find approved instructions or take you to the right module.",
  suggestions,
};

export default function PortalAssistant() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [started, setStarted] = useState(false);
  const [messages, setMessages] = useState([welcome]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  async function ask(value = text) {
    const question = value.trim();
    if (!question || busy) return;
    setStarted(true);
    setMessages((items) => [...items, { role: "user", text: question }]);
    setText("");
    setBusy(true);
    try {
      const reply = await api("/assistant/query", {
        method: "POST",
        body: JSON.stringify({ message: question }),
      });
      setMessages((items) => [
        ...items,
        {
          role: "assistant",
          text: reply.answer,
          sources: reply.sources,
          action: reply.action,
          suggestions: reply.suggestions,
        },
      ]);
    } catch (err) {
      setMessages((items) => [
        ...items,
        { role: "assistant", text: `I could not search the portal just now. ${err.message}` },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {open && (
        <section className="portal-assistant" aria-label="Portal Guide">
          <header>
            <img className="assistant-mini-avatar" src="/assets/branding/operations-portal-app-icon.png" alt="" />
            <div>
              <strong>Portal Guide</strong>
              <small>Portal Guide</small>
            </div>
            <button className="icon" onClick={() => setOpen(false)} aria-label="Close assistant">
              <X />
            </button>
          </header>

          {!started ? (
            <div className="assistant-intro">
              <div className="assistant-intro-banner">
                <img className="assistant-character" src="/assets/branding/operations-portal-app-icon.png" alt="Portal Guide" />
                <img className="assistant-organization-logo" src="/assets/branding/operations-portal-app-icon.png" alt="Mission Operations Portal" />
              </div>
              <div className="assistant-intro-copy">
                <span className="assistant-online"><i /> Online</span>
                <h2>Hello, I am your Portal Guide.</h2>
                <p>Ask me for approved guidance or let me take you to the right part of the portal.</p>
                <div className="assistant-intro-actions">
                  {suggestions.map((item) => (
                    <button key={item} onClick={() => ask(item)}>{item}</button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="assistant-thread">
              {messages.map((message, index) => (
                <article className={message.role} key={`${message.role}-${index}`}>
                  <p>{message.text}</p>
                  {message.sources?.length > 0 && (
                    <div className="assistant-sources">
                      {message.sources.map((source) => <span key={source.id}>{source.title}</span>)}
                    </div>
                  )}
                  {message.action && (
                    <button onClick={() => { navigate(message.action.route); setOpen(false); }}>
                      {message.action.label}
                    </button>
                  )}
                  {message.suggestions?.length > 0 && index === messages.length - 1 && (
                    <div className="assistant-suggestions">
                      {message.suggestions.map((item) => <button key={item} onClick={() => ask(item)}>{item}</button>)}
                    </div>
                  )}
                </article>
              ))}
              {busy && (
                <article className="assistant">
                  <p className="assistant-thinking"><i /><i /><i /></p>
                </article>
              )}
            </div>
          )}

          <form onSubmit={(event) => { event.preventDefault(); ask(); }}>
            <input
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Type your message"
            />
            <button disabled={busy || !text.trim()} aria-label="Send"><Send /></button>
          </form>
        </section>
      )}
      <button
        className="portal-assistant-launcher"
        onClick={() => setOpen((value) => !value)}
        aria-label="Open Portal Guide"
      >
        <span><img src="/assets/branding/operations-portal-app-icon.png" alt="" /></span>
        <i><MessageCircle /></i>
        {!open && <b><Sparkles /> Ask Guide</b>}
      </button>
    </>
  );
}
