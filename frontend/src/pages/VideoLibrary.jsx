import { Clock3, ExternalLink, Play, Plus, Video } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Badge, Empty, ErrorBox, Loading } from "../components/UI";
import { useTranslation } from "../i18n";
import { canAccess } from "../modules";

const blank = {
  title: "",
  description: "",
  url: "",
  category: "Microsoft 365",
  tags: "",
  duration_seconds: "",
  is_active: true,
};

export default function VideoLibrary() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const admin = canAccess(user, "can_access_admin");
  const [videos, setVideos] = useState(null);
  const [categories, setCategories] = useState([]);
  const [filter, setFilter] = useState("All");
  const [form, setForm] = useState(blank);
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");

  function load() {
    Promise.all([api("/videos"), api("/categories")])
      .then(([videoData, categoryData]) => {
        setVideos(videoData);
        setCategories(categoryData.filter((item) => item.is_active));
      })
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(
    () => videos?.filter((video) => filter === "All" || video.category === filter) || [],
    [videos, filter],
  );

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/videos", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          tags: form.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
          duration_seconds: form.duration_seconds ? Number(form.duration_seconds) : null,
        }),
      });
      setForm(blank);
      setShow(false);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!videos) return <><ErrorBox error={error} /><Loading /></>;

  return (
    <div>
      <div className="pagehead">
        <div>
          <span className="eyebrow">{t("selfService")}</span>
          <h1>{t("quickHelpVideos")}</h1>
          <p>{t("videosIntro")}</p>
        </div>
        {admin && <button className="primary" onClick={() => setShow(!show)}><Plus /> {t("addVideo")}</button>}
      </div>
      <ErrorBox error={error} />
      {show && (
        <form className="panel video-form" onSubmit={submit}>
          <div className="grid two">
            <label>{t("title")}<input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required /></label>
            <label>{t("category")}<select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>{categories.map((item) => <option key={item.id}>{item.name}</option>)}</select></label>
            <label>HTTPS video URL<input type="url" value={form.url} onChange={(event) => setForm({ ...form, url: event.target.value })} required /></label>
            <label>Duration in seconds<input type="number" min="1" value={form.duration_seconds} onChange={(event) => setForm({ ...form, duration_seconds: event.target.value })} /></label>
          </div>
          <label>{t("description")}<textarea rows="3" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} required /></label>
          <label>Search tags <span>comma separated</span><input value={form.tags} onChange={(event) => setForm({ ...form, tags: event.target.value })} /></label>
          <div className="actions"><button type="button" className="ghost" onClick={() => setShow(false)}>{t("cancel")}</button><button className="primary">{t("publish")}</button></div>
        </form>
      )}
      <div className="video-filter">
        <button className={filter === "All" ? "active" : ""} onClick={() => setFilter("All")}>{t("all")}</button>
        {categories.map((item) => <button key={item.id} className={filter === item.name ? "active" : ""} onClick={() => setFilter(item.name)}>{item.name}</button>)}
      </div>
      {filtered.length === 0 ? (
        <Empty title={t("noVideos")} text={t("videosIntro")} />
      ) : (
        <div className="video-grid">
          {filtered.map((video) => (
            <article className="panel video-card" key={video.id}>
              <div className="video-cover"><Video /><span><Play /></span></div>
              <div><Badge>{video.category}</Badge><h2>{video.title}</h2><p>{video.description}</p></div>
              <div className="video-meta">
                <span><Clock3 /> {video.duration_seconds ? `${Math.ceil(video.duration_seconds / 60)} min` : "Short guide"}</span>
                <a href={video.url} target="_blank" rel="noreferrer">Watch <ExternalLink /></a>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
