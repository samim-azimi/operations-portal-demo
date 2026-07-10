import { Check, ChevronDown, Languages } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "../i18n";

function Flag({ item }) {
  const [failed, setFailed] = useState(false);
  return failed
    ? <span className="flag-fallback" aria-hidden="true">{item.fallback}</span>
    : <img className="language-flag" src={item.flagImage} alt="" onError={() => setFailed(true)} />;
}

export default function LanguageSelector() {
  const { language, setLanguage, languages } = useTranslation();
  const [open, setOpen] = useState(false);
  const root = useRef(null);
  const selected = languages[language];
  useEffect(() => {
    const close = (event) => !root.current?.contains(event.target) && setOpen(false);
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);
  return <div className="language-selector" ref={root}>
    <button type="button" className="language-trigger" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
      <Languages size={15}/><Flag item={selected}/><span>{selected.label}</span><ChevronDown size={14}/>
    </button>
    {open && <div className="language-menu" role="menu">
      {Object.values(languages).map((item) => <button
        type="button" key={item.code} role="menuitemradio" aria-checked={language === item.code}
        onClick={() => { setLanguage(item.code); setOpen(false); }}
      >
        <Flag item={item}/><span>{item.label}</span>{language === item.code && <Check size={14}/>}
      </button>)}
    </div>}
  </div>;
}
