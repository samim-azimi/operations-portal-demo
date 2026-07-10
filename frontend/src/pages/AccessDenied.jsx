import { ArrowLeft, LockKeyhole } from "lucide-react";
import { Link } from "react-router-dom";

export default function AccessDenied() {
  return <div className="state-page">
    <div className="state-icon denied"><LockKeyhole/></div>
    <span className="eyebrow">Access restricted</span>
    <h1>You do not have access to this platform</h1>
    <p>Your Operations Portal permissions do not include this module. Contact an administrator if your responsibilities have changed.</p>
    <Link className="primary link" to="/workspace"><ArrowLeft/> Back to Workspace</Link>
  </div>;
}
