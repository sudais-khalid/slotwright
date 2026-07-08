"""Evaluation pipeline (FR-08): RL vs random vs rule-based over N seeded semesters.

Metrics per method (mean ± std across episodes):
- avg_attendance: mean attendance per event
- attendance_rate: attendance as share of expected audience
- conflict_count: total conflicts per semester
- venue_utilization: mean fill ratio (attendance / venue capacity)
- total_reward: episode reward
"""
import numpy as np

from rl.baselines import RandomScheduler, RuleBasedScheduler, run_episode
from rl.env import EventSchedulingEnv
from rl.q_learning import QLearningAgent


class _GreedyRL:
    name = "rl"

    def __init__(self, agent: QLearningAgent):
        self.agent = agent

    def act(self, env, obs, mask):
        return self.agent.act(env, obs, mask, greedy=True)


def _episode_metrics(total_reward: float, log: list[dict]) -> dict:
    att = [e["attendance"] for e in log]
    return {
        "avg_attendance": float(np.mean(att)),
        "attendance_rate": float(np.mean([e["attendance"] / e["expected_audience"] for e in log])),
        "conflict_count": int(sum(len(e["conflicts"]) for e in log)),
        "venue_utilization": float(np.mean([e["attendance"] / e["venue_capacity"] for e in log])),
        "total_reward": float(total_reward),
    }


def evaluate(dataset: dict, agent: QLearningAgent | None = None,
             episodes: int = 20) -> dict:
    """Returns {method: {metric: {mean, std}}, sample_log: {...}}."""
    methods = {
        "random": RandomScheduler(seed=123),
        "rule_based": RuleBasedScheduler(),
    }
    if agent is not None:
        methods["rl"] = _GreedyRL(agent)

    results, sample_logs = {}, {}
    for name, scheduler in methods.items():
        env = EventSchedulingEnv(dataset)
        runs = []
        for ep in range(episodes):
            total, log = run_episode(env, scheduler, seed=10_000 + ep)
            runs.append(_episode_metrics(total, log))
        sample_logs[name] = log  # last episode's full schedule for the dashboard
        results[name] = {
            metric: {
                "mean": round(float(np.mean([r[metric] for r in runs])), 3),
                "std": round(float(np.std([r[metric] for r in runs])), 3),
            }
            for metric in runs[0]
        }
    return {"metrics": results, "episodes": episodes, "sample_logs": sample_logs}
