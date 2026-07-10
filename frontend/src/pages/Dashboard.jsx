import {
  AlertTriangle,
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Gauge,
  ShieldCheck,
  Sparkles,
  Ticket,
  UsersRound,
  WandSparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Badge, ErrorBox, fmt, Loading } from "../components/UI";
import { useTranslation } from "../i18n";

const priorityWeight = { Critical: 4, High: 3, Medium: 2, Low: 1 };

export default function Dashboard() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/dashboard/stats").then(setData).catch((err) => setError(err.message));
  }, []);

  if (!data) {
    return (
      <>
        <ErrorBox error={error} />
        <Loading />
      </>
    );
  }

  const categoryMax = Math.max(1, ...Object.values(data.by_category));
  const confidence = Math.round(data.average_ai_confidence * 100);
  const coverage = Math.round(data.automation_coverage * 100);
  const closureRate = data.total_tickets
    ? Math.round(
        ((data.closed_tickets + data.resolved_tickets) / data.total_tickets) *
          100,
      )
    : 0;
  const smartQueue = [...data.recent_tickets]
    .filter((ticket) => !["Resolved", "Closed"].includes(ticket.status))
    .sort(
      (a, b) =>
        Number(b.human_approval_required && !b.human_approved) -
          Number(a.human_approval_required && !a.human_approved) ||
        priorityWeight[b.priority] - priorityWeight[a.priority],
    )
    .slice(0, 5);

  return (
    <div className="dashboard">
      <section className="command-hero">
        <div>
          <span className="kicker">
            <Sparkles size={14} /> Help Desk · {t("serviceOverview")}
          </span>
          <h1>{t("todaysSupport")}</h1>
          <p>
            Hi {user.full_name.split(" ")[0]}. There are{" "}
            <strong>{data.high_risk_tickets} high-risk tickets</strong> and{" "}
            <strong>{data.pending_approval} approval decisions</strong> waiting
            for review.
          </p>
        </div>
        <div className="hero-actions">
          <span className="live">
            <i /> {t("systemsOperational")}
          </span>
          <Link className="primary link" to="/tickets">
            {t("openQueue")} <ArrowRight size={17} />
          </Link>
        </div>
      </section>

      <ErrorBox error={error} />

      <div className="smart-insight">
        <div className="insight-icon">
          <WandSparkles />
        </div>
        <div>
          <span>What needs attention</span>
          <strong>
            {data.critical_tickets
              ? `${data.critical_tickets} critical ticket${data.critical_tickets > 1 ? "s" : ""} need immediate attention.`
              : "No critical incidents are currently open."}
          </strong>
          <p>
            Triage coverage is {coverage}% with {confidence}% average
            confidence.{" "}
            {data.low_confidence_tickets
              ? `${data.low_confidence_tickets} low-confidence recommendation should be reviewed manually.`
              : "All active recommendations are above the review threshold."}
          </p>
        </div>
        <Link to="/tickets">
          Review recommendations <ChevronRight size={16} />
        </Link>
      </div>

      <div className="statgrid advanced">
        <article>
          <div className="stat-icon blue">
            <Ticket />
          </div>
          <div>
            <span>{t("activeWorkload")}</span>
            <strong>{data.open_tickets}</strong>
            <small>{data.total_tickets} tickets all time</small>
          </div>
          <em className="metric neutral">Live</em>
        </article>
        <article>
          <div className="stat-icon red">
            <AlertTriangle />
          </div>
          <div>
            <span>{t("highRisk")}</span>
            <strong>{data.high_risk_tickets}</strong>
            <small>{data.critical_tickets} critical right now</small>
          </div>
          <em className="metric danger">Act now</em>
        </article>
        <article>
          <div className="stat-icon amber">
            <ShieldCheck />
          </div>
          <div>
            <span>{t("awaitingApproval")}</span>
            <strong>{data.pending_approval}</strong>
            <small>Human safety checkpoints</small>
          </div>
          <em className="metric warning">Review</em>
        </article>
        <article>
          <div className="stat-icon teal">
            <CheckCircle2 />
          </div>
          <div>
            <span>{t("resolutionRate")}</span>
            <strong>{closureRate}%</strong>
            <small>
              {data.closed_tickets + data.resolved_tickets} completed tickets
            </small>
          </div>
          <em className="metric good">Healthy</em>
        </article>
      </div>

      <div className="intelligence-grid">
        <section className="panel triage-health">
          <div className="panel-title">
            <div>
              <span className="eyebrow">AI performance</span>
              <h2>Triage intelligence health</h2>
              <p>Quality and automation guardrails across all requests.</p>
            </div>
            <BrainCircuit className="panel-icon" />
          </div>
          <div className="health-content">
            <div
              className="confidence-ring"
              style={{
                background: `conic-gradient(#19aa98 ${confidence}%, #e8edf4 0)`,
              }}
            >
              <div>
                <strong>{confidence}%</strong>
                <span>confidence</span>
              </div>
            </div>
            <div className="health-metrics">
              <Progress
                label="Automation coverage"
                value={coverage}
                detail={`${data.total_tickets} requests`}
              />
              <Progress
                label="Human-reviewed safety"
                value={
                  data.pending_approval
                    ? Math.max(
                        0,
                        Math.round(
                          (1 -
                            data.pending_approval /
                              Math.max(1, data.high_risk_tickets)) *
                            100,
                        ),
                      )
                    : 100
                }
                detail={`${data.pending_approval} pending`}
                tone="amber"
              />
              <Progress
                label="Assignment coverage"
                value={Math.round(
                  (1 -
                    data.unassigned_tickets / Math.max(1, data.open_tickets)) *
                    100,
                )}
                detail={`${data.unassigned_tickets} unassigned`}
                tone="violet"
              />
            </div>
          </div>
        </section>

        <section className="panel priority-mix">
          <div className="panel-title">
            <div>
              <span className="eyebrow">Risk distribution</span>
              <h2>Priority mix</h2>
              <p>All-time ticket severity.</p>
            </div>
            <Gauge className="panel-icon" />
          </div>
          <div className="priority-stack">
            {["Critical", "High", "Medium", "Low"].map((name) => {
              const count = data.by_priority[name] || 0;
              const percent = data.total_tickets
                ? Math.round((count / data.total_tickets) * 100)
                : 0;
              return (
                <div key={name}>
                  <Badge>{name}</Badge>
                  <span>{percent}%</span>
                  <strong>{count}</strong>
                </div>
              );
            })}
          </div>
        </section>
      </div>

      <div className="dashboard-grid detailed">
        <section className="panel chart">
          <div className="panel-title">
            <div>
              <span className="eyebrow">Demand intelligence</span>
              <h2>Requests by category</h2>
              <p>Where support demand is concentrating.</p>
            </div>
            <UsersRound className="panel-icon" />
          </div>
          {Object.entries(data.by_category)
            .sort((a, b) => b[1] - a[1])
            .map(([name, count]) => (
              <div className="bar-row rich" key={name}>
                <span>{name}</span>
                <div>
                  <i style={{ width: `${(count / categoryMax) * 100}%` }} />
                </div>
                <strong>{count}</strong>
                <small>{Math.round((count / data.total_tickets) * 100)}%</small>
              </div>
            ))}
        </section>

        <section className="panel status-board">
          <div className="panel-title">
            <div>
              <span className="eyebrow">Workflow pulse</span>
              <h2>Ticket lifecycle</h2>
              <p>Current flow across support stages.</p>
            </div>
            <Clock3 className="panel-icon" />
          </div>
          {Object.entries(data.by_status).map(([status, count]) => (
            <div className="status-line" key={status}>
              <div>
                <i className={status.toLowerCase().replaceAll(" ", "-")} />
                <span>{status}</span>
              </div>
              <strong>{count}</strong>
            </div>
          ))}
        </section>
      </div>

      <section className="panel smart-queue-preview">
        <div className="panel-title">
          <div>
            <span className="eyebrow">AI-prioritized work</span>
            <h2>Next best actions</h2>
            <p>Ordered by approval needs, severity, and freshness.</p>
          </div>
          <Link to="/tickets">
            View full queue <ArrowRight size={15} />
          </Link>
        </div>
        <div className="smart-ticket-list">
          {smartQueue.map((ticket, index) => (
            <Link to={`/tickets/${ticket.id}`} key={ticket.id}>
              <span className="queue-rank">{String(index + 1).padStart(2, "0")}</span>
              <div className="ticket-summary">
                <strong>{ticket.title}</strong>
                <span>
                  #{String(ticket.id).padStart(4, "0")} · {ticket.category} ·{" "}
                  {fmt(ticket.created_at)}
                </span>
              </div>
              {ticket.human_approval_required && !ticket.human_approved ? (
                <span className="approval-flag">
                  <ShieldCheck size={14} /> Approval
                </span>
              ) : (
                <span className="ai-flag">
                  <BrainCircuit size={14} />{" "}
                  {Math.round(
                    (ticket.ai_analysis?.confidence_score || 0) * 100,
                  )}
                  %
                </span>
              )}
              <Badge>{ticket.priority}</Badge>
              <ChevronRight size={17} />
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

function Progress({ label, value, detail, tone = "teal" }) {
  const safeValue = Math.min(100, Math.max(0, value));
  return (
    <div className="progress-metric">
      <div>
        <span>{label}</span>
        <strong>{safeValue}%</strong>
      </div>
      <div className="progress-track">
        <i className={tone} style={{ width: `${safeValue}%` }} />
      </div>
      <small>{detail}</small>
    </div>
  );
}
