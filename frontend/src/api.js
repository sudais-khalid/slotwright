const BASE = "/api";

async function get(path) {
  const res = await fetch(BASE + path);
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
  return res.json();
}

async function post(path, body) {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
  return res.json();
}

async function upload(path, file) {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(BASE + path, { method: "POST", body });
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
  return res.json();
}

export const api = {
  meta: () => get("/meta"),
  schedule: (method) => get(`/schedule?method=${method}`),
  train: (episodes) => post("/train", { episodes }),
  trainStatus: () => get("/train/status"),
  evaluate: (episodes) => get(`/evaluate?episodes=${episodes}`),
  useRealData: () => post("/data/use-real", {}),
  uploadFile: (kind, file) => upload(`/upload/${kind}`, file),
};

export function openTrainingSocket(onMessage, onClose) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/train`);
  ws.onmessage = (e) => onMessage(JSON.parse(e.data));
  ws.onclose = onClose;
  ws.onerror = onClose;
  return ws;
}

export const METHOD_LABELS = { rl: "RL agent", rule_based: "Rule-based", random: "Random" };
export const METHOD_COLORS = { rl: "#2f66ac", rule_based: "#a08015", random: "#8259b8" };
export const CATEGORY_COLORS = {
  workshop: "#3d6fa5",
  seminar: "#bc5b27",
  hackathon: "#22997a",
  career_fair: "#8259b8",
  guest_lecture: "#a08015",
  society_meeting: "#b34a85",
};
export const CATEGORY_LABELS = {
  workshop: "Workshop",
  seminar: "Seminar",
  hackathon: "Hackathon",
  career_fair: "Career fair",
  guest_lecture: "Guest lecture",
  society_meeting: "Society meeting",
};
