import { FileText, Inbox, Database } from "lucide-react";
import { useState } from "react";

import CGWorkflow from "./components/CGWorkflow.jsx";
import QueryPanel from "./components/QueryPanel.jsx";
import SinglePipeline from "./components/SinglePipeline.jsx";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function App() {
  const [activeTab, setActiveTab] = useState("single");
  const [crossNavigateRunId, setCrossNavigateRunId] = useState(null);

  function navigateToSingleRun(runId) {
    setCrossNavigateRunId(runId);
    setActiveTab("single");
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="sidebar">
          <div className="sidebar-brand">
            <div className="brand-icon"></div>
            <h1>Trade Document Validation</h1>
          </div>

          <nav className="nav-menu">
            <button
              className={activeTab === "single" ? "active" : ""}
              onClick={() => setActiveTab("single")}
              type="button"
            >
              <FileText size={18} />
              <span>Single Doc Pipeline</span>
            </button>
            <button
              className={activeTab === "inbox" ? "active" : ""}
              onClick={() => setActiveTab("inbox")}
              type="button"
            >
              <Inbox size={18} />
              <span>Inbox Workflow</span>
            </button>
            <button
              className={activeTab === "query" ? "active" : ""}
              onClick={() => setActiveTab("query")}
              type="button"
            >
              <Database size={18} />
              <span>Natural Query</span>
            </button>
          </nav>
        </aside>

        <section className="content">
          {activeTab === "single" && (
            <SinglePipeline apiBase={API_BASE} initialRunId={crossNavigateRunId} />
          )}
          {activeTab === "inbox" && (
            <div className="dashboard-page">
               <header className="page-header">
                 <h2>Inbox Triage Workflow</h2>
                 <p className="muted">Simulate and process incoming supplier emails.</p>
               </header>
               <CGWorkflow apiBase={API_BASE} />
            </div>
          )}
          {activeTab === "query" && (
            <div className="dashboard-page">
               <header className="page-header">
                 <h2>Natural Language Analytics</h2>
                 <p className="muted">Ask questions about your operations data in plain English.</p>
               </header>
               <QueryPanel apiBase={API_BASE} onNavigateToRun={navigateToSingleRun} />
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
