import React, { useState } from "react";
import { METHOD_COLORS, METHOD_LABELS } from "../api.js";

const W = 280, H = 190, PAD = { l: 10, r: 10, t: 26, b: 24 };

/* One metric, one bar per method. Direct value labels above each bar (only 3
   marks, so labeling all is the selective choice); method names under bars,
   so identity never rides on color alone. */
export default function MethodBars({ title, sub, data, format = (v) => v.toFixed(1) }) {
  const [hover, setHover] = useState(null);
  const methods = Object.keys(data);
  const max = Math.max(...methods.map((m) => data[m].mean + (data[m].std || 0)));
  const bw = (W - PAD.l - PAD.r) / methods.length;
  const y = (v) => PAD.t + (1 - v / (max || 1)) * (H - PAD.t - PAD.b);

  return (
    <div className="sheet chart-box">
      <h3>{title}</h3>
      <div className="sub">{sub}</div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto" }} role="img" aria-label={title}
        onMouseLeave={() => setHover(null)}>
        <line className="axis-line" x1={PAD.l} x2={W - PAD.r} y1={H - PAD.b} y2={H - PAD.b} />
        {methods.map((m, i) => {
          const cx = PAD.l + bw * i + bw / 2;
          const top = y(data[m].mean);
          const barW = Math.min(46, bw - 16);
          return (
            <g key={m}
              onMouseMove={(e) => setHover({ m, cx: e.clientX, cy: e.clientY })}>
              <rect x={cx - barW / 2} y={top} width={barW} height={H - PAD.b - top}
                fill={METHOD_COLORS[m]} rx="3" />
              {/* square off the bottom corners: bars anchor flat on the baseline */}
              <rect x={cx - barW / 2} y={H - PAD.b - 3} width={barW} height={3} fill={METHOD_COLORS[m]} />
              {data[m].std > 0 && (
                <line x1={cx} x2={cx} y1={y(data[m].mean - data[m].std)} y2={y(data[m].mean + data[m].std)}
                  stroke="#1c2a3a" strokeWidth="1" opacity="0.55" />
              )}
              <text className="direct-label" x={cx} y={top - 6} textAnchor="middle">{format(data[m].mean)}</text>
              <text x={cx} y={H - 8} textAnchor="middle">{METHOD_LABELS[m]}</text>
            </g>
          );
        })}
      </svg>
      {hover && (
        <div className="tooltip" style={{ left: hover.cx + 12, top: hover.cy - 34 }}>
          {METHOD_LABELS[hover.m]}: {format(data[hover.m].mean)} ± {format(data[hover.m].std)}
        </div>
      )}
    </div>
  );
}
