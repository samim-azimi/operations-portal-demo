import { Inbox } from "lucide-react";
import { useTranslation } from "../i18n";

export function Badge({ children, type }) {
  const value = String(children || "");
  return <span className={`badge ${type || value.toLowerCase().replaceAll(" ", "-")}`}>{children}</span>;
}

export function Empty({ title, text }) {
  const { language } = useTranslation();
  const defaults = {
    en: ["Nothing here yet", "New records will appear here."],
    fr: ["Rien à afficher", "Les nouveaux éléments apparaîtront ici."],
    fa: ["هنوز چیزی اینجا نیست", "موارد جدید در اینجا نمایش داده می‌شود."],
    ps: ["تر اوسه دلته څه نشته", "نوي معلومات به دلته ښکاره شي."],
  };
  const fallback = defaults[language] || defaults.en;
  return <div className="empty"><Inbox/><h3>{title || fallback[0]}</h3><p>{text || fallback[1]}</p></div>;
}

export function Loading() {
  const { language } = useTranslation();
  const labels = { en: "Loading…", fr: "Chargement…", fa: "در حال بارگذاری…", ps: "بارېږي…" };
  return <div className="loading"><i/><span>{labels[language] || labels.en}</span></div>;
}

export function ErrorBox({ error }) {
  return error ? <div className="alert error">{error}</div> : null;
}

export const fmt = (date) => new Intl.DateTimeFormat(
  document.documentElement.lang || "en",
  { dateStyle: "medium", timeStyle: "short" },
).format(new Date(date));
