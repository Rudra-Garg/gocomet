import { AlertTriangle, CheckCircle2, FilePenLine } from "lucide-react";
import { useEffect, useState } from "react";

const ACTIONS = {
  auto_approve: { label: "Auto approve", icon: CheckCircle2 },
  draft_amendment: { label: "Draft amendment", icon: FilePenLine },
  flag_review: { label: "Flag review", icon: AlertTriangle },
};

export default function RouterDecision({ decision, error }) {
  const action = decision?.action;
  const [email, setEmail] = useState("");

  useEffect(() => {
    setEmail(decision?.amendment_email || "");
  }, [decision?.amendment_email]);

  if (error) {
    return <section className="decision error">Run error: {error}</section>;
  }

  if (!action) {
    return <section className="decision pending">Run a document to see the decision.</section>;
  }

  const Icon = ACTIONS[action]?.icon || AlertTriangle;

  return (
    <section className={`decision ${action}`}>
      <div className="decision-title">
        <Icon size={22} />
        <strong>{ACTIONS[action]?.label || action}</strong>
      </div>
      <p>{decision.reasoning}</p>
      {action === "draft_amendment" && (
        <textarea
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          rows={7}
          aria-label="Amendment email"
        />
      )}
    </section>
  );
}

