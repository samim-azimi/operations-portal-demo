import { ArrowRight, FileText, Image, ShieldCheck, UploadCloud, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { ErrorBox } from "../components/UI";
import { useTranslation } from "../i18n";

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["image/png", "image/jpeg", "image/webp", "application/pdf", "text/plain"];

export default function SubmitTicket() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const [options, setOptions] = useState({ categories: [], locations: [] });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [files, setFiles] = useState([]);
  const [form, setForm] = useState({
    category: "", location: "", device_name: "", title: "",
    description: "", urgency: "Medium", attachment_url: "",
  });

  useEffect(() => {
    Promise.all([api("/categories"), api("/locations")])
      .then(([categories, locations]) => {
        setOptions({
          categories: categories.filter((item) => item.is_active !== false),
          locations: locations.filter((item) => item.is_active !== false),
        });
        setForm((current) => ({
          ...current,
          location: current.location || locations.find((item) => item.name === "Remote")?.name || locations[0]?.name || "Remote",
        }));
      })
      .catch((err) => setError(err.message));
  }, []);

  const change = (event) => setForm({ ...form, [event.target.name]: event.target.value });

  function addFiles(fileList) {
    setError("");
    const incoming = Array.from(fileList);
    if (files.length + incoming.length > 5) return setError("You can attach up to five files.");
    const invalid = incoming.find((file) => {
      const extension = file.name.split(".").pop()?.toLowerCase();
      return ((!ALLOWED_TYPES.includes(file.type) && !(!file.type && ["txt", "log"].includes(extension))) || file.size > MAX_FILE_BYTES);
    });
    if (invalid) return setError(`${invalid.name} is not supported. Use PNG, JPG, WEBP, PDF, TXT, or LOG under 5 MB.`);
    setFiles((current) => [...current, ...incoming.filter((file) =>
      !current.some((existing) => existing.name === file.name && existing.size === file.size && existing.lastModified === file.lastModified)
    )]);
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const ticket = await api("/tickets", { method: "POST", body: JSON.stringify(form) });
      for (const file of files) {
        const body = new FormData();
        body.append("file", file);
        await api(`/tickets/${ticket.id}/attachments`, { method: "POST", body });
      }
      navigate(`/tickets/${ticket.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="submit-page">
      <div className="pagehead"><div><span className="eyebrow">Help Desk</span><h1>Create Ticket</h1><p>Describe the issue and attach a screenshot if it helps.</p></div></div>
      <form className="panel ticket-form human-form" onSubmit={submit}>
        <ErrorBox error={error} />
        <div className="grid two">
          <label>{t("category")}<select name="category" value={form.category} onChange={change}><option value="">{t("none")}</option>{options.categories.filter((item) => item.name !== "None").map((item) => <option key={item.id}>{item.name}</option>)}</select></label>
          <label>Priority<select name="urgency" value={form.urgency} onChange={change}>{["Low", "Medium", "High", "Critical"].map((value) => <option key={value}>{value}</option>)}</select></label>
        </div>
        <label>Subject<input name="title" placeholder="Brief summary of the issue" value={form.title} onChange={change} required /></label>
        <label>Description<textarea name="description" rows="7" maxLength="10000" placeholder={t("detailsPlaceholder")} value={form.description} onChange={change} required /></label>
        <details className="ticket-options"><summary>Additional details</summary><div className="grid two">
          <label>{t("location")}<select name="location" value={form.location} onChange={change} required>{options.locations.map((item) => <option key={item.id}>{item.name}</option>)}</select></label>
          <label>{t("deviceTag")}<input name="device_name" placeholder={t("exampleTag")} value={form.device_name} onChange={change}/></label>
        </div></details>
        <div className="form-section compact-upload">
          <div className="section-heading"><div><h3>Attachment <small>optional</small></h3><p>{t("filesHint")}</p></div></div>
          <div className={dragging ? "upload-zone dragging" : "upload-zone"}
            onDragEnter={(e) => { e.preventDefault(); setDragging(true); }} onDragOver={(e) => e.preventDefault()}
            onDragLeave={() => setDragging(false)} onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files); }}
            onClick={() => inputRef.current?.click()}>
            <UploadCloud /><strong>{t("dropFiles")}</strong><span>{t("fileRules")}</span>
            <input ref={inputRef} type="file" multiple hidden accept=".png,.jpg,.jpeg,.webp,.pdf,.txt,.log" onChange={(e) => addFiles(e.target.files)} />
          </div>
          {files.length > 0 && <div className="upload-list">{files.map((file, index) => <div key={`${file.name}-${file.lastModified}`}>
            {file.type.startsWith("image/") ? <Image /> : <FileText />}<div><strong>{file.name}</strong><span>{(file.size / 1024).toFixed(1)} KB</span></div>
            <button type="button" title="Remove file" onClick={() => setFiles((current) => current.filter((_, i) => i !== index))}><X /></button>
          </div>)}</div>}
        </div>
        <div className="form-footer"><span><ShieldCheck/>Secure upload</span><button className="primary" disabled={busy}>{busy ? t("creatingRequest") : "Submit"}<ArrowRight size={18}/></button></div>
      </form>
    </div>
  );
}
