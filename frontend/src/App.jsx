import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import EvaluationView from "./views/EvaluationView.jsx";
import ScheduleView from "./views/ScheduleView.jsx";
import TrainingView from "./views/TrainingView.jsx";

const TABS = [
  { id: "schedule", label: "Schedule" },
  { id: "training", label: "Training" },
  { id: "evaluation", label: "Evaluation" },
];

const initialTab = () => {
  const h = location.hash.replace("#", "");
  return TABS.some((t) => t.id === h) ? h : "schedule";
};

export default function App() {
  const [tab, setTabState] = useState(initialTab);
  const setTab = (id) => {
    location.hash = id;
    setTabState(id);
  };
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState(null);

  const refreshMeta = () => api.meta().then(setMeta).catch((e) => setError(e.message));
  useEffect(() => { refreshMeta(); }, []);

  return (
    <>
      <header className="masthead">
        <h1>Event Datesheet</h1>
        <span className="fileno">RL SCHEDULER · BSAI-23F-0050</span>
        <span className="spacer" />
        {meta && (
          <span className="status-chip">
            <span className={"dot" + (meta.agent_trained ? "" : " off")} />
            {meta.agent_trained ? "agent trained" : "agent not trained"}
            &nbsp;·&nbsp;{meta.n_students} students · {meta.n_events} events
          </span>
        )}
      </header>

      <nav className="tabs" role="tablist" aria-label="Dashboard sections">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>

      <main>
        {error && <p className="error-note">Backend unreachable: {error}. Start it with `uvicorn app.main:app` in backend/.</p>}
        {meta && tab === "schedule" && <ScheduleView meta={meta} />}
        {meta && tab === "training" && <TrainingView onTrained={refreshMeta} />}
        {meta && tab === "evaluation" && <EvaluationView agentTrained={meta.agent_trained} />}
      </main>
    </>
  );
}
