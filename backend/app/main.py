"""FastAPI app: REST API + WebSocket for the scheduling dashboard.

Run from backend/:  uvicorn app.main:app --reload --port 8000
"""
import asyncio

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from evaluation.evaluate import evaluate
from rl.baselines import RandomScheduler, RuleBasedScheduler, run_episode
from rl.env import EventSchedulingEnv
from simulator.config import CATEGORY_LIST, DAYS, DEPARTMENTS, EXAM_WEEKS, N_WEEKS, SEMESTERS, SLOT_LABELS

from .state import state

app = FastAPI(title="AI Event Scheduler", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)


class SimulateRequest(BaseModel):
    seed: int = 42
    n_students: int = Field(480, ge=16, le=5000)
    n_events: int = Field(40, ge=5, le=200)


class TrainRequest(BaseModel):
    episodes: int = Field(10000, ge=10, le=50000)
    # Defaults found by sweep: low gamma works best because events couple only
    # weakly (venue clashes), so long bootstrap chains mostly add noise.
    alpha: float = Field(0.1, gt=0, le=1)
    gamma: float = Field(0.4, ge=0, le=1)


@app.get("/api/meta")
def meta():
    return {
        "days": DAYS, "slots": SLOT_LABELS, "weeks": N_WEEKS,
        "exam_weeks": EXAM_WEEKS, "categories": CATEGORY_LIST,
        "departments": DEPARTMENTS, "semesters": SEMESTERS,
        "venues": [{k: v[k] for k in ("venue_id", "name", "capacity", "building")}
                   for v in state.dataset["venues"]],
        "n_students": len(state.dataset["students"]),
        "n_events": len(state.dataset["events"]),
        "agent_trained": state.agent is not None,
    }


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    if state.training.snapshot()["running"]:
        raise HTTPException(409, "Training in progress; wait for it to finish.")
    counts = state.regenerate(seed=req.seed, n_students=req.n_students, n_events=req.n_events)
    return {"status": "regenerated", "counts": counts, "seed": req.seed}


@app.post("/api/train")
def train(req: TrainRequest):
    if not state.start_training(req.episodes, req.alpha, req.gamma):
        raise HTTPException(409, "Training already running.")
    return {"status": "started", "episodes": req.episodes}


@app.get("/api/train/status")
def train_status():
    return state.training.snapshot()


@app.websocket("/ws/train")
async def train_ws(ws: WebSocket):
    """Streams training progress snapshots (rewards trimmed to the tail)."""
    await ws.accept()
    last_ep = -1
    try:
        while True:
            snap = state.training.snapshot()
            if snap["episode"] != last_ep or not snap["running"]:
                last_ep = snap["episode"]
                snap["rewards"] = snap["rewards"][-200:]
                await ws.send_json(snap)
                if not snap["running"] and snap["episode"] > 0:
                    break
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        pass


def _scheduler_for(method: str):
    if method == "random":
        return RandomScheduler(seed=0)
    if method == "rule_based":
        return RuleBasedScheduler()
    if method == "rl":
        if state.agent is None:
            raise HTTPException(400, "No trained agent yet — run /api/train first.")
        from evaluation.evaluate import _GreedyRL
        return _GreedyRL(state.agent)
    raise HTTPException(422, f"Unknown method '{method}'")


@app.get("/api/schedule")
def schedule(method: str = "rl", seed: int = 99):
    """Roll one semester with the chosen method and return the full schedule (FR-03, FR-09)."""
    scheduler = _scheduler_for(method)
    env = EventSchedulingEnv(state.dataset)
    total, log = run_episode(env, scheduler, seed=seed)
    for entry in log:
        entry["method"] = method
    state.store.replace_all("schedule_log", log)
    return {"method": method, "total_reward": round(total, 2), "schedule": log}


@app.get("/api/evaluate")
def run_evaluation(episodes: int = 20):
    """Compare RL vs random vs rule-based (FR-08)."""
    result = evaluate(state.dataset, agent=state.agent, episodes=episodes)
    state.store.replace_all("results", [{"metrics": result["metrics"], "episodes": episodes}])
    return result
