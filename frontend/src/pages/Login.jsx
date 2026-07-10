import { ArrowRight, CheckCircle2, Headphones, LockKeyhole, MessageSquareText, TicketCheck } from "lucide-react";
import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth";
import LanguageSelector from "../components/LanguageSelector";
import { ErrorBox } from "../components/UI";
import { useTranslation } from "../i18n";
import { useBranding } from "../branding";

const loginBackgrounds = [
  "/assets/branding/operations-portal-app-icon.png",
];

export default function Login() {
  const { user, signIn } = useAuth();
  const { t } = useTranslation();
  const { branding } = useBranding();
  const location = useLocation();
  const requestedNext = new URLSearchParams(location.search).get("next");
  const next = requestedNext?.startsWith("/") && !requestedNext.startsWith("//")
    ? requestedNext
    : (user?.role === "user" ? "/my-tickets" : "/workspace");
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [backgroundImage] = useState(
    () => loginBackgrounds[Math.floor(Math.random() * loginBackgrounds.length)],
  );

  if (user) return <Navigate to={next} replace />;

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try { await signIn(email, password); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  const demos = [
    ["Demo Admin", "admin@example.com", "admin123"],
    ["Demo Manager", "manager@example.com", "manager123"],
    ["Demo Inventory", "inventory@example.com", "inventory123"],
    ["Demo Stock", "stock@example.com", "stock123"],
    ["Demo User", "user@example.com", "user123"],
  ];

  return (
    <div
      className="login-page professional-login login-photo-bg"
      style={{ "--login-bg-image": `url(${backgroundImage})` }}
    >
      <section className="login-story">
        <div className="brand light">
          <img className="login-brand-logo" src="/assets/branding/operations-portal-app-icon.png" alt="Mission Operations Portal" />
          <div><strong>{branding.organization_name}</strong>{branding.organization_name!=="Mission Operations Portal"&&<span>Operations Portal</span>}</div>
        </div>
        <div className="story-copy">
          <span className="login-overline"><Headphones size={16} /> {t("secureWorkspace")}</span>
          <h1>{t("platformName")}</h1>
          <p>{t("platformSubtitle")}</p>
          <div className="login-benefits">
            <div><TicketCheck /><span>{t("trackRequests")}</span></div>
            <div><MessageSquareText /><span>{t("directConversation")}</span></div>
            <div><CheckCircle2 /><span>{t("usefulGuides")}</span></div>
          </div>
        </div>
        <small>2026 Mission Operations Portal demo</small>
      </section>

      <section className="login-panel">
        <div className="login-language"><LanguageSelector /></div>
        <form className="login-card" onSubmit={submit}>
          <div className="lock"><LockKeyhole /></div>
          <span className="eyebrow">{t("secureWorkspace")}</span>
          <h2>{t("welcomeBack")}</h2>
          <p>{t("loginIntro")}</p>
          <ErrorBox error={error} />
          <label>{t("email")}
            <input type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </label>
          <label>{t("password")}
            <input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </label>
          <button className="primary login-submit" disabled={busy}>
            {busy ? t("signingIn") : t("signIn")} {!busy && <ArrowRight size={17} />}
          </button>
          <details className="demo-access">
            <summary>{t("demoAccounts")}</summary>
            <p>{t("chooseAccount")}</p>
            <div>{demos.map(([label, demoEmail, demoPassword]) => (
              <button type="button" key={label} onClick={() => { setEmail(demoEmail); setPassword(demoPassword); }}>{label}</button>
            ))}</div>
          </details>
          <small className="privacy-note"><LockKeyhole size={13} /> {t("privacyNote")}</small>
        </form>
      </section>
    </div>
  );
}
