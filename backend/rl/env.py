"""EventSchedulingEnv — Gymnasium-compliant scheduling environment (FR-02, FR-03).

Episode: one semester of event requests, presented in week order. For each
request the agent picks a (day, start slot, venue) placement — or defers the
event to the next week (the last action index). Valid placements require BOTH
the venue to be free AND the target student group to have high common
availability, enforced through action masking (FR-03). Events may span
several consecutive slots (`duration_slots`), e.g. a 3-hour workshop occupies
3 real class periods; every slot in the span must clear the same checks.

Observation (MultiDiscrete): [category, audience_bucket, priority-1,
exam_week_flag, week_load_bucket, department, semester_idx] — deliberately
coarse so the same vector doubles as the tabular Q-Learning state key.

The grid shape (days/slots/weeks/departments/semesters) is read from the
dataset itself rather than hardcoded, so the same env runs unchanged against
the synthetic simulator (6 slots/day) or a real department's timetable (9
real class periods/day, per FR-04/12 of the requirements doc).
"""
import gymnasium as gym
import numpy as np
from gymnasium import spaces

from simulator.config import CATEGORY_LIST
from simulator.conflicts import detect_conflicts
from simulator.free_slots import group_free_ratio, group_interest_share

MASK_FREE_RATIO = 0.4   # a slot counts as usable if >= 40% of the group is free
MAX_DEFERS = 2

CONFLICT_PENALTIES = {
    "venue_double_booking": -15.0,
    "venue_unavailable": -15.0,
    "exam_week": -10.0,
    "lecture_overlap": -8.0,
    "major_event_clash": -5.0,
    "venue_too_small": -3.0,
}


class EventSchedulingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, dataset: dict, seed: int | None = None):
        super().__init__()
        self.dataset = dataset
        self.venues = dataset["venues"]
        self.n_venues = len(self.venues)
        self.n_days = len(dataset["days"])
        self.n_slots = len(dataset["slots"])
        self.n_weeks = dataset["weeks"]
        self.departments = dataset.get("departments") or sorted({s["department"] for s in dataset["students"]})
        self.semesters = dataset.get("semesters") or sorted({s["semester"] for s in dataset["students"]})

        self.exam_weeks = set()
        self.holiday_weeks = set()
        for entry in dataset["calendar"]:
            if entry["type"] == "exam":
                self.exam_weeks.update(entry["weeks"])
            elif entry["type"] == "holiday":
                self.holiday_weeks.update(entry["weeks"])

        # Precompute per-group free-ratio grids and per-(group, category) interest
        self._free = {}
        self._interest = {}
        for ev in dataset["events"]:
            key = (ev["department"], ev["semester"])
            if key not in self._free:
                self._free[key] = group_free_ratio(dataset["students"], *key, self.n_days, self.n_slots)
            ikey = key + (ev["category"],)
            if ikey not in self._interest:
                self._interest[ikey] = group_interest_share(dataset["students"], *key, ev["category"])

        self.n_place_actions = self.n_days * self.n_slots * self.n_venues
        self.action_space = spaces.Discrete(self.n_place_actions + 1)  # +1 = defer
        self.observation_space = spaces.MultiDiscrete(
            [len(CATEGORY_LIST), 3, 3, 2, 3, len(self.departments), len(self.semesters)]
        )
        self._rng = np.random.default_rng(seed)

    # ---------- helpers ----------
    def decode_action(self, a: int) -> tuple[int, int, int] | None:
        """Returns (day, start_slot, venue_idx), or None for the defer action."""
        if a == self.n_place_actions:
            return None
        v, rest = a % self.n_venues, a // self.n_venues
        s, d = rest % self.n_slots, rest // self.n_slots
        return d, s, v

    def _current(self) -> dict:
        return self._queue[self._i]

    def _duration(self, ev: dict) -> int:
        return max(1, min(ev.get("duration_slots", 1), self.n_slots))

    def _event_week(self, ev: dict) -> int:
        return min(self.n_weeks, ev["week"] + self._defers.get(ev["event_id"], 0))

    def _obs(self) -> np.ndarray:
        ev = self._current()
        week = self._event_week(ev)
        aud = ev["expected_audience"]
        aud_bucket = 0 if aud < 50 else (1 if aud < 150 else 2)
        load = sum(1 for (w, *_,) in self.schedule if w == week)
        return np.array([
            CATEGORY_LIST.index(ev["category"]),
            aud_bucket,
            ev["priority"] - 1,
            int(week in self.exam_weeks),
            min(load, 2),
            self.departments.index(ev["department"]),
            self.semesters.index(ev["semester"]),
        ], dtype=np.int64)

    def _span_ok(self, ev: dict, d: int, s: int, venue: dict, week: int, free: np.ndarray) -> bool:
        dur = self._duration(ev)
        if s + dur > self.n_slots:
            return False
        for sl in range(s, s + dur):
            if free[d, sl] < MASK_FREE_RATIO:
                return False
            if [d, sl] not in venue["available_slots"]:
                return False
            if (week, d, sl, venue["venue_id"]) in self.schedule:
                return False
        return True

    def action_masks(self) -> np.ndarray:
        ev = self._current()
        week = self._event_week(ev)
        free = self._free[(ev["department"], ev["semester"])]
        mask = np.zeros(self.action_space.n, dtype=bool)
        for d in range(self.n_days):
            for s in range(self.n_slots):
                if free[d, s] < MASK_FREE_RATIO:  # necessary condition for any span starting here
                    continue
                for v, venue in enumerate(self.venues):
                    if venue["capacity"] < 0.4 * ev["expected_audience"]:
                        continue
                    if not self._span_ok(ev, d, s, venue, week, free):
                        continue
                    mask[(d * self.n_slots + s) * self.n_venues + v] = True
        if self._defers.get(ev["event_id"], 0) < MAX_DEFERS and week < self.n_weeks:
            mask[self.n_place_actions] = True
        if not mask.any():  # fallback: nothing clean exists, allow every placement
            mask[: self.n_place_actions] = True
        return mask

    # ---------- gym API ----------
    def reset(self, seed: int | None = None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self._queue = sorted(self.dataset["events"], key=lambda e: e["week"])
        self._i = 0
        self._defers = {}
        self.schedule = {}   # (week, day, slot, venue_id) -> event
        self.log = []        # one entry per scheduled event (FR schedule_log shape)
        return self._obs(), {"action_mask": self.action_masks()}

    def step(self, action: int):
        ev = self._current()
        week = self._event_week(ev)
        decoded = self.decode_action(int(action))

        if decoded is None:  # defer to next week
            self._defers[ev["event_id"]] = self._defers.get(ev["event_id"], 0) + 1
            self._queue.append(self._queue.pop(self._i))  # requeue at the end
            reward = -1.0
            done = False
            info = {"deferred": True, "action_mask": self.action_masks()}
            return self._obs(), reward, done, False, info

        d, s, v = decoded
        dur = self._duration(ev)
        venue = self.venues[v]
        free_grid = self._free[(ev["department"], ev["semester"])]
        span = list(range(s, min(s + dur, self.n_slots)))
        free = float(min(free_grid[d, sl] for sl in span))
        conflicts: list[str] = []
        for sl in span:
            for c in detect_conflicts(ev, week, d, sl, venue, free_grid[d, sl], self.exam_weeks, self.schedule):
                if c not in conflicts:
                    conflicts.append(c)

        interest = self._interest[(ev["department"], ev["semester"], ev["category"])]
        exam_factor = 0.4 if week in self.exam_weeks else 1.0
        holiday_factor = 0.5 if week in self.holiday_weeks else 1.0
        expected = ev["expected_audience"] * free * (0.5 + 0.5 * interest) * exam_factor * holiday_factor
        noise = self._rng.normal(0, 0.05 * ev["expected_audience"])
        attendance = float(np.clip(expected + noise, 0, venue["capacity"]))

        reward = 10.0 * attendance / ev["expected_audience"]
        fill = attendance / venue["capacity"]
        if 0.4 <= fill <= 0.95:
            reward += 3.0       # well-matched venue
        elif fill < 0.15:
            reward -= 3.0       # cavernous hall for a tiny crowd
        reward += sum(CONFLICT_PENALTIES[c] for c in conflicts)

        for sl in span:
            self.schedule[(week, d, sl, venue["venue_id"])] = ev
        self.log.append({
            "event_id": ev["event_id"], "category": ev["category"],
            "name": ev.get("name", ev["event_id"]),
            "assigned_week": week, "assigned_day": d, "assigned_slot": s,
            "duration_slots": dur,
            "assigned_venue": venue["venue_id"],
            "common_free_slot_score": round(float(free), 3),
            "attendance": round(attendance, 1),
            "expected_audience": ev["expected_audience"],
            "venue_capacity": venue["capacity"],
            "conflicts": conflicts,
            "reward_received": round(float(reward), 2),
        })

        self._i += 1
        done = self._i >= len(self._queue)
        info = {"attendance": attendance, "conflicts": conflicts}
        if not done:
            info["action_mask"] = self.action_masks()
            obs = self._obs()
        else:
            obs = np.zeros(7, dtype=np.int64)
        return obs, float(reward), done, False, info
