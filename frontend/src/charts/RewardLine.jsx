import React, { useMemo, useRef, useState } from "react";

const W = 720, H = 260, PAD = { l: 46, r: 14, t: 12, b: 28 };

function movingAvg(values, window = 50) {
  const out = [];
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= window) sum -= values[i - window];
    out.push(sum / Math.min(i + 1, window));
  }
  return out;
}

/* Reward-per-episode line: raw series thin & light, 50-episode moving average
   as the readable 2px line. Crosshair + tooltip per the dataviz interaction spec. */
export default function RewardLine({ rewards, rawColor = "#a9c3e0", avgColor = "#2f66ac" }) {
  const ref = useRef(null);
  const [hover, setHover] = useState(null);
  const avg = useMemo(() => movingAvg(rewards), [rewards]);

  if (rewards.length < 2) return <p className="note">Reward curve appears here once training starts.</p>;

  const lo = Math.min(...rewards), hi = Math.max(...rewards);
  const x = (i) => PAD.l + (i / (rewards.length - 1)) * (W - PAD.l - PAD.r);
  const y = (v) => PAD.t + (1 - (v - lo) / (hi - lo || 1)) * (H - PAD.t - PAD.b);
  const path = (vals) => vals.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");

  const yTicks = [lo, (lo + hi) / 2, hi];

  const onMove = (e) => {
    const rect = ref.current.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const i = Math.round(((px - PAD.l) / (W - PAD.l - PAD.r)) * (rewards.length - 1));
    if (i >= 0 && i < rewards.length) setHover({ i, cx: e.clientX, cy: e.clientY });
    else setHover(null);
  };

  return (
    <>
      <div className="chart-legend">
        <span className="key"><span className="swatch" style={{ background: rawColor, width: 14, height: 3 }} />episode reward</span>
        <span className="key"><span className="swatch" style={{ background: avgColor, width: 14, height: 3 }} />50-episode average</span>
      </div>
      <svg ref={ref} viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto" }}
        role="img" aria-label="Training reward per episode with 50-episode moving average"
        onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        {yTicks.map((t) => (
          <g key={t}>
            <line className="grid-line" x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} />
            <text x={PAD.l - 6} y={y(t) + 3} textAnchor="end">{Math.round(t)}</text>
          </g>
        ))}
        <line className="axis-line" x1={PAD.l} x2={W - PAD.r} y1={H - PAD.b} y2={H - PAD.b} />
        <text x={PAD.l} y={H - 8}>ep 1</text>
        <text x={W - PAD.r} y={H - 8} textAnchor="end">ep {rewards.length}</text>
        <path d={path(rewards)} fill="none" stroke={rawColor} strokeWidth="1" />
        <path d={path(avg)} fill="none" stroke={avgColor} strokeWidth="2" />
        {hover && (
          <>
            <line x1={x(hover.i)} x2={x(hover.i)} y1={PAD.t} y2={H - PAD.b} stroke="#88929c" strokeWidth="1" />
            <circle cx={x(hover.i)} cy={y(avg[hover.i])} r="4" fill={avgColor} stroke="#fdfdfb" strokeWidth="2" />
          </>
        )}
      </svg>
      {hover && (
        <div className="tooltip" style={{ left: hover.cx + 12, top: hover.cy - 34 }}>
          ep {hover.i + 1} · reward {rewards[hover.i].toFixed(1)} · avg {avg[hover.i].toFixed(1)}
        </div>
      )}
    </>
  );
}
