import React, { useRef, useState } from "react";
import { api } from "../api.js";

const SLOTS = [
  { kind: "timetables", label: "Semester timetables", hint: "Weekly class timetable, semesters 1–8 (PDF, or the CSV template)" },
  { kind: "venues", label: "Venue timetable", hint: "Classroom/lab availability and capacities (PDF or CSV)" },
  { kind: "events", label: "Semester event plan", hint: "The events societies want scheduled this semester (PDF or CSV)" },
];

function UploadSlot({ kind, label, hint, onDone }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const pick = async (file) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.uploadFile(kind, file);
      setResult(res);
      onDone();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="sheet tile" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div className="k">{label}</div>
      <div className="u">{hint}</div>
      <input ref={inputRef} type="file" accept=".pdf,.csv" style={{ display: "none" }}
        onChange={(e) => pick(e.target.files[0])} />
      <button className="btn ghost" style={{ alignSelf: "flex-start" }} disabled={busy}
        onClick={() => inputRef.current.click()}>
        {busy ? "Uploading…" : "Choose file"}
      </button>
      {result && <span className="note">saved · dataset now has {result.counts.events} events, {result.counts.students} students</span>}
      {error && <span className="error-note">{error}</span>}
    </div>
  );
}

export default function DataView({ meta, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const reimport = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.useRealData();
      onChanged();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="sheet tile" style={{ marginBottom: 18 }}>
        <div className="k">Current data source</div>
        <div className="v" style={{ fontSize: 18 }}>
          {meta.source === "real_fall2025" ? "Department of AI — Fall 2025 (real)" : "Synthetic demo data"}
        </div>
        <div className="u">
          {meta.n_students} students · {meta.n_events} events · {meta.venues.length} venues ·{" "}
          {meta.departments.join(", ")} · semesters {meta.semesters.join(", ")}
        </div>
      </div>

      <p className="note" style={{ marginBottom: 14 }}>
        Upload a new timetable, venue list, or event plan below — the whole real dataset is
        re-parsed and re-seeded after each upload. Retrain the agent (Training tab) afterwards so
        its policy matches the new calendar.
      </p>

      <div className="eval-grid">
        {SLOTS.map((s) => (
          <UploadSlot key={s.kind} {...s} onDone={onChanged} />
        ))}
      </div>

      <div className="controls section-gap">
        <button className="btn" onClick={reimport} disabled={busy}>
          {busy ? "Re-importing…" : "Re-import from real_data/"}
        </button>
        <span className="note">Use this after replacing files directly on disk instead of uploading here.</span>
      </div>
      {error && <p className="error-note">{error}</p>}
      {meta.import_error && <p className="error-note">Last import warning: {meta.import_error}</p>}
    </>
  );
}
