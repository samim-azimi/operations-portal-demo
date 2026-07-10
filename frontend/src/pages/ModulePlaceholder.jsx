import { ArrowLeft, Clock3, LockKeyhole } from "lucide-react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { canAccess, moduleById } from "../modules";

export default function ModulePlaceholder({ moduleId }) {
  const { user } = useAuth();
  const module = moduleById(moduleId);
  if (!module) return <Navigate to="/workspace"/>;
  if (!canAccess(user, module.permission)) return <Navigate to="/access-denied"/>;
  const Icon = module.icon;
  return <div className="module-placeholder">
    <Link className="back" to="/workspace"><ArrowLeft/> Back to Workspace</Link>
    <section className="placeholder-hero panel">
      <div className={`module-icon module-${module.id}`}><Icon/></div>
      <span className="module-status coming"><Clock3/> Coming Soon</span>
      <h1>{module.name}</h1>
      <p>{module.description}</p>
      <div className="access-confirmed"><LockKeyhole/><span><strong>Access confirmed</strong>This module is included in your workspace permissions and will appear here when released.</span></div>
    </section>
  </div>;
}
