import React, { useEffect, useMemo, useState } from "react";
import { api, CATEGORY_COLORS, CATEGORY_LABELS, METHOD_LABELS } from "../api.js";

function Chit({ entry }) {
  const clash = entry.conflicts.length > 0;
  const title = `${entry.event_id} · ${CATEGORY_LABELS[entry.category]} · venue ${entry.assigned_venue} · ` +
    `expected ${entry.expected_audience}, attended ~${Math.round(entry.attendance)}` +
    (clash ? ` · conflicts: ${entry.conflicts.join(", ")}` : "");
  return (
    <div className={"chit" + (clash ? " clash" : "")} style={{ "--cat": CATEGORY_COLORS[entry.category] }} title={title}>
      {clash && <span className="stamp">CLASH</span>}
      <span className="code">{entry.event_id}</span>
      <span className="cat">{CATEGORY_LABELS[entry.category]}</span>
      <span className="meta">{entry.assigned_venue} · ~{Math.round(entry.attendance)} att.</span>
    </div>
  );
}

export default function ScheduleView({ meta }) {
  const [method, setMethod] = useState(meta.agent_trained ? "rl" : "rule_based");
  const [week, setWeek] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setData(null);
    setError(null);
    api.schedule(method).then(setData).catch((e) => setError(e.message));
  }, [method]);

  const byWeek = useMemo(() => {
    const map = {};
    for (const e of data?.schedule ?? []) (map[e.assigned_week] ??= []).push(e);
    return map;
  }, [data]);

  const weekEntries = byWeek[week] ?? [];
  const cell = (d, s) => weekEntries.filter((e) => e.assigned_day === d && e.assigned_slot === s);
  const isExam = meta.exam_weeks.includes(week);
  const usedCategories = [...new Set((data?.schedule ?? []).map((e) => e.category))];

  const clean = (data?.schedule ?? []).filter((e) => e.conflicts.length === 0).length;
  const total = data?.schedule?.length ?? 0;

  return (
    <>
      <div className="controls">
        <div className="seg" role="group" aria-label="Scheduling method">
          {Object.entries(METHOD_LABELS).map(([id, label]) => (
            <button key={id} aria-pressed={method === id} onClick={() => setMethod(id)}
              disabled={id === "rl" && !meta.agent_trained}
              title={id === "rl" && !meta.agent_trained ? "Train the agent first (Training tab)" : undefined}>
              {label}
            </button>
          ))}
        </div>
        <div className="week-stepper">
          <button className="btn ghost" onClick={() => setWeek((w) => Math.max(1, w - 1))} aria-label="Previous week">‹</button>
          <span className="wk">Week {week} / {meta.weeks}</span>
          <button className="btn ghost" onClick={() => setWeek((w) => Math.min(meta.weeks, w + 1))} aria-label="Next week">›</button>
          {isExam && <span className="exam-flag">EXAM WEEK</span>}
        </div>
        {data && <span className="note">semester reward {data.total_reward} · {weekEntries.length} event{weekEntries.length === 1 ? "" : "s"} this week</span>}
      </div>

      {error && <p className="error-note">{error}</p>}
      {!data && !error && <p className="note">Building the {METHOD_LABELS[method].toLowerCase()} schedule…</p>}

      {data && (
        <div className="sched-layout">
          <div className="sheet">
            <table className="datesheet">
              <caption>{METHOD_LABELS[method]} — week {week}</caption>
              <thead>
                <tr>
                  <th className="slot-head" scope="col">Slot</th>
                  {meta.days.map((d) => <th key={d} scope="col">{d}</th>)}
                </tr>
              </thead>
              <tbody>
                {meta.slots.map((slot, s) => (
                  <tr key={slot}>
                    <td className="slot-label">{slot}</td>
                    {meta.days.map((_, d) => (
                      <td key={d}>{cell(d, s).map((e) => <Chit key={e.event_id} entry={e} />)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="legend">
              {usedCategories.map((c) => (
                <span className="key" key={c}>
                  <span className="swatch" style={{ background: CATEGORY_COLORS[c] }} />{CATEGORY_LABELS[c]}
                </span>
              ))}
            </div>
          </div>

          <div className="tiles" style={{ gridTemplateColumns: "1fr" }}>
            <div className="sheet tile">
              <div className="k">Clean placements</div>
              <div className="v">{clean}/{total}</div>
              <div className="u">events without any conflict</div>
            </div>
            <div className="sheet tile">
              <div className="k">Conflicts</div>
              <div className="v">{(data.schedule ?? []).reduce((n, e) => n + e.conflicts.length, 0)}</div>
              <div className="u">total across the semester</div>
            </div>
            <div className="sheet tile">
              <div className="k">Avg free-slot score</div>
              <div className="v">
                {(weekEntries.length ? weekEntries : data.schedule)
                  .reduce((a, e) => a + e.common_free_slot_score, 0) /
                  ((weekEntries.length ? weekEntries : data.schedule).length || 1) * 100 | 0}%
              </div>
              <div className="u">target group availability {weekEntries.length ? "this week" : "overall"}</div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
