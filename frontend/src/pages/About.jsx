import { BarChart3, Blocks, BookOpenCheck, Container, Grid2X2, LifeBuoy, PackageSearch, ShieldCheck, Warehouse } from "lucide-react";
import { useBranding } from "../branding";

const features=[
  [Grid2X2,"Unified workspace","One permission-aware portal for every operational module."],
  [LifeBuoy,"Help Desk","Ticket triage, collaboration, approval, knowledge, and reporting."],
  [PackageSearch,"IMS","Inventory assets, staff assignment, and valuation."],
  [Warehouse,"Stock","Category-first requests, stock cards, movements, and annual reports."],
  [BarChart3,"Dashboards","Assigned published dashboards and embedded Power BI analytics."],
  [BookOpenCheck,"Connected knowledge","Approved guidance helps teams reuse known solutions."],
  [ShieldCheck,"Controlled access","Permissions are enforced in both the interface and API."],
  [Blocks,"Modular architecture","Each module keeps focused routes, data, and performance boundaries."],
  [Container,"Docker deployment","Frontend, API, and PostgreSQL launch together."],
];

export default function About(){
  const {branding,logoUrl,defaultLogoLight}=useBranding();
  return <div>
    <section className="about-hero">
      <img src={logoUrl||defaultLogoLight} alt={branding.organization_name} className="about-org-logo"/>
      <span className="kicker">Internal operations platform</span>
      <h1>Mission Operations Portal</h1>
      <p>Mission Operations Portal is an internal modular operations system for inventory, stock, digital signing, communication, reports, dashboards, and future procurement workflows.</p>
      <small>{branding.organization_name}</small>
    </section>
    <section className="feature-grid faza-features">{features.map(([Icon,title,text])=><article className="panel" key={title}><Icon/><h2>{title}</h2><p>{text}</p></article>)}</section>
    <section className="panel architecture">
      <span className="eyebrow">Product structure</span>
      <h2>Clear separation with shared governance</h2>
      <div className="flow"><span>Operations Portal</span><i>→</i><span>Permissions</span><i>→</i><span>Help Desk</span><i>+</i><span>IMS</span><i>+</i><span>Stock</span><i>+</i><span>Dashboards</span></div>
      <p>IMS manages asset records and staff assignments. Stock manages consumables, employee requests, stock cards, movements, and stock reports.</p>
    </section>
  </div>;
}
