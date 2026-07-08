import React, { useEffect, useState } from "react";
import { api, METHOD_LABELS } from "../api.js";
import MethodBars from "../charts/MethodBars.jsx";

const PANELS = [
  { key: "total_reward", title: "Semester reward", sub: "mean total reward per episode", fmt: (v) => v.toFixed(0) },
  { key: "attendance_rate", title: "Attendance rate", sub: "share of expected audience that attends", fmt: (v) => (v * 100).toFixed(1) + "%" },
  { key: "conflict_count", title: "Conflicts", sub: "per semester — lower is better", fmt: (v) => v.toFixed(1) },
  { key: "venue_utilization", title: "Venue utilization", sub: "mean fill ratio of booked venues", fmt: (v) => (v * 100).toFixed(1) + "%" },
];

export default function EvaluationView({ agentTrained }) {
  const [episodes, setEpisodes] = useState(20);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => { run(); }, []); // the comparison is this screen's content

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.evaluate(episodes));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const metrics = result?.metrics;
  const methods = metrics ? Object.keys(metrics) : [];
  const bestFor = (key) => {
    if (!metrics) return null;
    const better = key === "conflict_count" ? Math.min : Math.max;
    return methods.reduce((a, b) => (better(metrics[a][key].mean, metrics[b][key].mean) === metrics[a][key].mean ? a : b));
  };

  return (
    <>
      <div className="controls">
        <label>
          Semesters per method
          <input type="number" min="5" max="100" value={episodes}
            onChange={(e) => setEpisodes(+e.target.value)} disabled={busy} />
        </label>
        <button className="btn" onClick={run} disabled={busy}>
          {busy ? "Comparing…" : "Run comparison"}
        </button>
        {!agentTrained && <span className="note">The agent isn't trained yet, so the comparison covers the two baselines only.</span>}
      </div>
      {error && <p className="error-note">{error}</p>}
      {!result && !busy && <p className="note">Runs every method over {episodes} simulated semesters and compares them on the four project metrics.</p>}

      {metrics && (
        <>
          <div className="eval-grid">
            {PANELS.map((p) => (
              <MethodBars key={p.key} title={p.title} sub={p.sub} format={p.fmt}
                data={Object.fromEntries(methods.map((m) => [m, metrics[m][p.key]]))} />
            ))}
          </div>

          <div className="sheet section-gap">
            <table className="data-table">
              <caption>All metrics — mean ± std over {result.episodes} semesters</caption>
              <thead>
                <tr>
                  <th scope="col">Method</th>
                  {PANELS.map((p) => <th key={p.key} scope="col">{p.title}</th>)}
                </tr>
              </thead>
              <tbody>
                {methods.map((m) => (
                  <tr key={m}>
                    <td>{METHOD_LABELS[m]}</td>
                    {PANELS.map((p) => (
                      <td key={p.key} className={bestFor(p.key) === m ? "best" : ""}>
                        {p.fmt(metrics[m][p.key].mean)} ± {p.fmt(metrics[m][p.key].std)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
