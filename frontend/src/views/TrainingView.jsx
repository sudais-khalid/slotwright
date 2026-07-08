import React, { useEffect, useRef, useState } from "react";
import { api, openTrainingSocket } from "../api.js";
import RewardLine from "../charts/RewardLine.jsx";

export default function TrainingView({ onTrained }) {
  const [episodes, setEpisodes] = useState(10000);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);

  // Pick up an already-running or past run on mount
  useEffect(() => {
    api.trainStatus().then((s) => {
      setStatus(s);
      if (s.running) listen();
    }).catch(() => {});
    return () => wsRef.current?.close();
  }, []);

  const listen = () => {
    wsRef.current?.close();
    wsRef.current = openTrainingSocket(
      (snap) => {
        setStatus(snap);
        if (!snap.running && snap.episode > 0) onTrained();
      },
      () => {} // socket closes when training ends; status already captured
    );
  };

  const start = async () => {
    setError(null);
    try {
      await api.train(episodes);
      listen();
    } catch (e) {
      setError(e.message);
    }
  };

  const rewards = status?.rewards ?? [];
  const running = status?.running ?? false;
  const best = rewards.length ? Math.max(...rewards) : null;

  return (
    <>
      <div className="controls">
        <label>
          Episodes
          <input type="number" min="10" max="50000" step="500" value={episodes}
            onChange={(e) => setEpisodes(+e.target.value)} disabled={running} />
        </label>
        <button className="btn" onClick={start} disabled={running}>
          {running ? "Training…" : "Start training"}
        </button>
        {running && <span className="note">episode {status.episode} of {status.total_episodes}</span>}
        {!running && status?.episode > 0 && <span className="note">last run: {status.episode} episodes</span>}
      </div>
      {error && <p className="error-note">{error}</p>}
      {status?.error && <p className="error-note">Training failed: {status.error}</p>}

      <div className="tiles">
        <div className="sheet tile">
          <div className="k">Episodes run</div>
          <div className="v">{status?.episode ?? 0}</div>
        </div>
        <div className="sheet tile">
          <div className="k">Avg reward · last 50</div>
          <div className="v">{status?.avg_reward_last_50 ?? "—"}</div>
        </div>
        <div className="sheet tile">
          <div className="k">Best episode</div>
          <div className="v">{best !== null ? best.toFixed(1) : "—"}</div>
          <div className="u">within the streamed window</div>
        </div>
      </div>

      <div className="sheet chart-box section-gap">
        <h3>Training reward</h3>
        <div className="sub">
          {rewards.length > 0 && status?.total_episodes > 200
            ? `showing the most recent ${rewards.length} episodes`
            : "cumulative reward per training episode"}
        </div>
        <RewardLine rewards={rewards} />
      </div>
    </>
  );
}
