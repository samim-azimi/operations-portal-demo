import { BookOpen, ChevronLeft, ChevronRight, Plus, Tags } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Badge, Empty, ErrorBox, Loading } from "../components/UI";
import { useTranslation } from "../i18n";
import { canAccess } from "../modules";

const blank = { title: "", category: "Network", problem_description: "", solution: "", tags: "" };

export default function KnowledgeBase() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const admin = canAccess(user, "can_access_admin");
  const [articles, setArticles] = useState(null);
  const [meta, setMeta] = useState({ total: 0, pages: 0 });
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState(blank);
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");

  function load() {
    api(`/knowledge-base?page=${page}&page_size=20`).then((data) => {
      setArticles(data.items);
      setMeta(data);
    }).catch((err) => setError(err.message));
    api("/categories").then(setCategories).catch(() => {});
  }
  useEffect(load, [page]);

  async function submit(event) {
    event.preventDefault();
    try {
      await api("/knowledge-base", { method: "POST", body: JSON.stringify({
        ...form, tags: form.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
      }) });
      setForm(blank); setShow(false); load();
    } catch (err) { setError(err.message); }
  }

  async function addCategory() {
    const name = window.prompt(t("add") + " " + t("category"));
    if (!name) return;
    try {
      await api("/categories", { method: "POST", body: JSON.stringify({
        name, description: `${name} support requests`, is_active: true,
      }) });
      load();
    } catch (err) { setError(err.message); }
  }

  return <div>
    <div className="pagehead"><div><span className="eyebrow">{t("knowledgeBase")}</span><h1>{t("knowledgeBase")}</h1><p>{t("knowledgeIntro")}</p></div>
      {admin && <div className="actions"><button className="secondary" onClick={addCategory}><Tags/> {t("add")} {t("category")}</button>
        <button className="primary" onClick={() => setShow(!show)}><Plus/> {t("newArticle")}</button></div>}
    </div>
    <ErrorBox error={error}/>
    {show && <form className="panel kb-form" onSubmit={submit}>
      <div className="panel-title"><h2>{t("newArticle")}</h2></div>
      <div className="grid two">
        <label>{t("title")}<input value={form.title} onChange={(e) => setForm({...form,title:e.target.value})} required/></label>
        <label>{t("category")}<select value={form.category} onChange={(e) => setForm({...form,category:e.target.value})}>{categories.map((item) => <option key={item.id}>{item.name}</option>)}</select></label>
      </div>
      <label>{t("description")}<textarea rows="3" value={form.problem_description} onChange={(e) => setForm({...form,problem_description:e.target.value})} required/></label>
      <label>{t("approvedSolution")}<textarea rows="4" value={form.solution} onChange={(e) => setForm({...form,solution:e.target.value})} required/></label>
      <label>Tags<input value={form.tags} onChange={(e) => setForm({...form,tags:e.target.value})}/></label>
      <div className="actions"><button type="button" className="ghost" onClick={() => setShow(false)}>{t("cancel")}</button><button className="primary">{t("publish")}</button></div>
    </form>}
    {!articles ? <Loading/> : articles.length === 0 ? <Empty title={t("knowledgeBase")} text={t("knowledgeIntro")}/> :
      <><div className="kb-grid">{articles.map((article) => <article className="panel kb-card" key={article.id}>
        <div className="kb-icon"><BookOpen/></div><div><Badge>{article.category}</Badge><h2>{article.title}</h2><p>{article.problem_description}</p>
          <div className="solution"><strong>{t("approvedSolution")}</strong><p>{article.solution}</p></div>
          <div className="taglist">{article.tags.map((tag) => <span key={tag}>#{tag}</span>)}</div>
        </div></article>)}</div>
      {meta.pages > 1 && <div className="pagination"><button className="ghost" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}><ChevronLeft/> Previous</button><span>Page {page} of {meta.pages}</span><button className="ghost" disabled={page >= meta.pages} onClick={() => setPage((value) => value + 1)}>Next <ChevronRight/></button></div>}</>}
  </div>;
}
