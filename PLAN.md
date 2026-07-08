# Project Plan — AI-Powered Student Event Scheduling Using Reinforcement Learning

**Student:** Muhammad Sudais Khalid (BSAI-23F-0050) · **Course:** Reinforcement Learning, Semester 6
**Source:** Project_Requirements_Analysis_Document.pdf (FR-01 … FR-09)

---

## 1. System Architecture

Four layers, matching the block diagram in the requirements document (Section 11):

```
┌────────────────────────────────────────────────────────────┐
│  FRONTEND — React + Vite dashboard (3 screens)             │
│  Weekly Schedule · Training Progress · Evaluation Compare  │
└───────────────▲────────────────────────────────────────────┘
                │ REST + WebSocket (live training updates)
┌───────────────┴────────────────────────────────────────────┐
│  BACKEND — FastAPI (Python 3.11+)                          │
│  /simulate /train /schedule /evaluate /metrics endpoints   │
├────────────────────────────────────────────────────────────┤
│  RL CORE — Gymnasium env + agents                          │
│  EventSchedulingEnv · QLearningAgent · (DQN stretch)       │
│  RandomScheduler · RuleBasedScheduler baselines            │
├────────────────────────────────────────────────────────────┤
│  DATA — MongoDB (NoSQL, per Section 12)                    │
│  students · events · venues · calendar · schedule_log      │
└────────────────────────────────────────────────────────────┘
```

### Tech stack
| Layer | Choice | Why |
|---|---|---|
| RL environment | Gymnasium (custom env) | FR-02 requires Gymnasium compliance |
| Agent | Tabular Q-Learning first, DQN (PyTorch) as stretch | Doc says "Q-Learning or DQN depending on action space size" |
| Backend API | FastAPI + Uvicorn | Async, auto OpenAPI docs, WebSocket support for live reward curve |
| Database | MongoDB (motor async driver) | Doc specifies NoSQL document collections |
| Frontend | React 18 + Vite + Tailwind | Fast dev loop; design via frontend-design skill |
| Charts | Recharts (styled per dataviz skill) | Reward curve, comparison bars, schedule grid |

### Repository layout
```
Project/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, routers, CORS
│   │   ├── routers/              # simulate, train, schedule, evaluate
│   │   ├── db.py                 # MongoDB connection + collections
│   │   └── ws.py                 # WebSocket: live training progress
│   ├── simulator/
│   │   ├── generators.py         # synthetic students/events/venues/calendar (FR-01)
│   │   └── free_slots.py         # common free-slot intersection (FR-04)
│   ├── rl/
│   │   ├── env.py                # EventSchedulingEnv (Gymnasium) (FR-02, FR-03, FR-05)
│   │   ├── q_learning.py         # tabular agent (FR-06)
│   │   ├── dqn.py                # stretch goal
│   │   └── baselines.py          # random + rule-based (FR-07)
│   ├── evaluation/
│   │   └── evaluate.py           # metrics pipeline (FR-08)
│   └── tests/
├── frontend/
│   └── src/
│       ├── pages/ScheduleView    # Screen 1 (FR-09)
│       ├── pages/TrainingView    # Screen 2
│       └── pages/EvaluationView  # Screen 3
├── docs/                          # MDP formalization, defense slides
└── PLAN.md
```

---

## 2. MDP Formalization (Objective 4)

**Episode** = one semester of incoming event requests, scheduled one at a time.

**State** (per incoming event request):
- Current event features: category, expected audience, duration, priority
- Calendar context: week index, exam-week flag, remaining events
- Availability summary: per (day × slot) — venue-free count, target-group free ratio (from timetable intersection)
- Occupancy: which slots already hold scheduled events this week

**Action:** discrete choice of `(day, time_slot, venue)`.
With ~5 days × 6 slots × ~8 venues = **240 actions** → tabular Q-Learning is feasible only with state discretization; use **action masking** (FR-03: only slots where venue is free AND group availability ≥ threshold are valid).

**Reward** (FR-05 penalties + attendance signal):
| Signal | Value (initial, tune later) |
|---|---|
| Expected attendance (audience × group-free ratio × interest match) | + up to 10 |
| Venue fit (capacity vs audience within band) | +3 / −3 if badly mismatched |
| Same-day major-event clash | −5 |
| Lecture/lab overlap for target group | −8 |
| Exam-week placement | −10 |
| Venue double-booking (should be masked; safety net) | −15 |

---

## 3. Phased Plan

### Phase 0 — Scaffold (Week 1)
- Git init, Python venv, `backend/` + `frontend/` scaffolds, MongoDB local instance (or Atlas free tier).
- CI-lite: pytest + ruff.

### Phase 1 — Simulator & Data Layer (Weeks 1–2) → FR-01
- Generators: ~500 students (dept, semester, weekly timetable, interests, attendance history), ~40 events/semester, ~8 venues (capacity 20–500), academic calendar (16 weeks, 2 exam weeks, holidays).
- Seed all five MongoDB collections; seedable RNG for reproducible experiments.
- **Checkpoint:** seeded DB inspectable; unit tests on generator invariants.

### Phase 2 — Free-Slot Calculator & Conflict Detection (Week 3) → FR-04, FR-05
- `common_free_slots(department, semester) -> {(day, slot): free_ratio}` by intersecting timetables.
- Conflict detectors: lecture overlap, exam week, double-booking, capacity mismatch, major-event clash.
- **Checkpoint:** tests proving known-conflict fixtures are caught.

### Phase 3 — Gymnasium Environment (Weeks 4–5) → FR-02, FR-03
- `EventSchedulingEnv(gym.Env)` with `reset()`, `step()`, `action_masks()`.
- Validate with `gymnasium.utils.env_checker`.
- **Checkpoint:** random rollouts run a full episode without invariant violations.

### Phase 4 — Baselines (Week 5) → FR-07
- Random scheduler (uniform over masked-valid actions).
- Rule-based: greedy — earliest slot with highest free-ratio and best capacity fit.
- **Checkpoint:** both produce full-semester schedules + logged metrics.

### Phase 5 — RL Agent (Weeks 6–8) → FR-06
- Tabular Q-Learning with discretized state, ε-greedy over masked actions, reward tracking per episode.
- Hyperparameter sweep (α, γ, ε-decay); persist Q-table + training curve to `schedule_log`.
- Stretch: DQN (PyTorch) if tabular state space proves too coarse.
- **Checkpoint:** reward curve trends upward; beats random baseline.

### Phase 6 — Evaluation Pipeline (Week 9) → FR-08
- Run RL vs random vs rule-based over N=30 seeded semesters.
- Metrics: avg attendance, conflict count, venue utilization; mean ± std, stored per method.
- **Checkpoint:** comparison table reproducible from one command.

### Phase 7 — Backend API (Weeks 9–10)
- `POST /simulate` (regenerate data), `POST /train` (background task + WebSocket progress), `POST /schedule` (one event request → decision, FR-03), `GET /schedule/week/{n}`, `GET /evaluate`, `GET /metrics`.
- **Checkpoint:** full flow drivable from OpenAPI docs page.

### Phase 8 — Frontend Dashboard (Weeks 10–12) → FR-09
Built with the **frontend-design** skill (distinctive, non-templated aesthetic) and **dataviz** skill for all charts.
- **Screen 1 — Weekly Schedule:** day × slot grid, events colored by category, venue tags, conflict highlights.
- **Screen 2 — Training Progress:** live reward-per-episode line (WebSocket), episode count, moving-average policy reward.
- **Screen 3 — Evaluation Comparison:** grouped bar charts per metric (RL vs random vs rule-based).
- **Checkpoint:** all three screens live against real backend data.

### Phase 9 — Defense Package (Weeks 12–13)
- Docs: MDP justification, experiment results, limitations (Objective 8).
- Optional: dockerize with **vibe-ship** skill for a one-command demo.
- Dry-run demo script for viva.

---

## 4. Requirements Traceability

| FR | Covered by |
|---|---|
| FR-01 | Phase 1 generators |
| FR-02 | Phase 3 Gymnasium env |
| FR-03 | Phase 3 action masking + Phase 7 `/schedule` |
| FR-04 | Phase 2 free-slot calculator |
| FR-05 | Phase 2 detectors + Phase 3 reward |
| FR-06 | Phase 5 training loop |
| FR-07 | Phase 4 baselines |
| FR-08 | Phase 6 evaluation pipeline |
| FR-09 | Phase 8 dashboard |

## 5. Risks & Mitigations
- **Action space too large for tabular Q** → aggressive state discretization + masking first; fall back to DQN (explicitly allowed by doc).
- **RL fails to beat rule-based** → reward shaping iterations budgeted in Phase 5; rule-based is deliberately greedy/myopic so sequential credit assignment is the RL edge.
- **MongoDB overhead for a prototype** → keep a JSON-file fallback behind the same repository interface.
- **Scope creep on frontend** → three screens only, per Section 13; no auth, no mobile (out of scope per doc).
