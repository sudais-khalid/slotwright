"""Backend test suite: generators (FR-01), free slots (FR-04), conflicts (FR-05),
Gymnasium compliance (FR-02), masking (FR-03), baselines (FR-07), training (FR-06)."""
import numpy as np
import pytest

from rl.baselines import RandomScheduler, RuleBasedScheduler, run_episode
from rl.env import EventSchedulingEnv, MASK_FREE_RATIO
from rl.q_learning import QLearningAgent
from simulator.config import CATEGORY_LIST, N_DAYS, N_SLOTS, N_WEEKS
from simulator.conflicts import detect_conflicts
from simulator.free_slots import group_free_ratio
from simulator.generators import generate_dataset


@pytest.fixture(scope="module")
def dataset():
    return generate_dataset(seed=7, n_students=160, n_events=25)


def test_generator_invariants(dataset):
    assert len(dataset["events"]) == 25
    for s in dataset["students"]:
        cells = {tuple(c) for c in s["weekly_timetable"]}
        assert len(cells) == len(s["weekly_timetable"])  # no duplicate busy cells
        assert all(0 <= d < N_DAYS and 0 <= sl < N_SLOTS for d, sl in cells)
        assert 1 <= len(s["interests"]) <= 3
    for e in dataset["events"]:
        assert 1 <= e["week"] <= N_WEEKS and e["priority"] in (1, 2, 3)
        assert e["category"] in CATEGORY_LIST
    weeks = [e["week"] for e in dataset["events"]]
    assert weeks == sorted(weeks)  # events arrive in week order


def test_generator_reproducible():
    a, b = generate_dataset(seed=3, n_students=32, n_events=5), generate_dataset(seed=3, n_students=32, n_events=5)
    assert a["events"] == b["events"] and a["students"] == b["students"]


def test_free_ratio_intersection(dataset):
    grid = group_free_ratio(dataset["students"], "AI", 6)
    assert grid.shape == (N_DAYS, N_SLOTS)
    assert grid.min() >= 0.0 and grid.max() <= 1.0
    # Group shares a base timetable, so grid must contain both busy and free cells
    assert (grid < 0.2).any() and (grid > 0.8).any()


def test_conflict_detection(dataset):
    ev = dict(dataset["events"][0], expected_audience=300, priority=3)
    venue = dict(dataset["venues"][0])  # small 40-seat room
    venue["available_slots"] = [[0, 0]]
    other = dict(ev, event_id="EOTHER")
    schedule = {(8, 0, 0, "VX"): other}
    conflicts = detect_conflicts(ev, week=8, day=0, slot=0, venue=venue,
                                 free_ratio=0.2, exam_weeks={8, 16}, schedule=schedule)
    assert {"lecture_overlap", "exam_week", "venue_too_small", "major_event_clash"} <= set(conflicts)
    assert detect_conflicts(ev, 3, 0, 0, dict(dataset["venues"][6]), 0.9, {8}, {}) == []


def test_env_gymnasium_compliance(dataset):
    from gymnasium.utils.env_checker import check_env
    check_env(EventSchedulingEnv(dataset), skip_render_check=True)


def test_action_mask_validity(dataset):
    env = EventSchedulingEnv(dataset, seed=0)
    obs, info = env.reset(seed=0)
    mask = info["action_mask"]
    assert mask.any()
    ev = env._current()
    free = env._free[(ev["department"], ev["semester"])]
    for a in np.flatnonzero(mask):
        decoded = env.decode_action(int(a))
        if decoded is None:
            continue
        d, s, v = decoded
        venue = env.venues[v]
        assert free[d, s] >= MASK_FREE_RATIO
        assert [d, s] in venue["available_slots"]


def test_full_episode_schedules_every_event(dataset):
    env = EventSchedulingEnv(dataset, seed=1)
    total, log = run_episode(env, RandomScheduler(seed=1), seed=1)
    assert len(log) == len(dataset["events"])
    assert len(env.schedule) == len(dataset["events"])  # no double-booked keys


def test_rule_based_beats_random(dataset):
    env = EventSchedulingEnv(dataset)
    rnd = np.mean([run_episode(env, RandomScheduler(seed=i), seed=i)[0] for i in range(5)])
    rule = np.mean([run_episode(env, RuleBasedScheduler(), seed=i)[0] for i in range(5)])
    assert rule > rnd


def test_q_learning_improves(dataset):
    env = EventSchedulingEnv(dataset, seed=0)
    agent = QLearningAgent(n_actions=env.action_space.n, seed=0)
    history = agent.train(env, episodes=300)

    class Greedy:
        def act(self, env, obs, mask):
            return agent.act(env, obs, mask, greedy=True)

    greedy_reward, _ = run_episode(env, Greedy(), seed=999)
    # The learned greedy policy must clearly beat the exploratory early episodes
    assert greedy_reward > np.mean(history[:10])


def test_q_table_save_load(tmp_path, dataset):
    env = EventSchedulingEnv(dataset, seed=0)
    agent = QLearningAgent(n_actions=env.action_space.n, seed=0)
    agent.train(env, episodes=5)
    p = agent.save(tmp_path / "q.pkl")
    loaded = QLearningAgent.load(p)
    obs, info = env.reset(seed=0)
    assert loaded.act(env, obs, info["action_mask"]) == agent.act(env, obs, info["action_mask"])
