"""Random and rule-based baseline schedulers (FR-07).

Both act through the same env + action mask as the RL agent, so every method
faces identical constraints and the comparison is fair. The rule-based
scheduler is deliberately greedy and myopic: best local slot, never defers —
the sequential planning gap is what the RL agent is supposed to exploit.
"""
import numpy as np

from simulator.config import N_SLOTS

from .env import EventSchedulingEnv


class RandomScheduler:
    name = "random"

    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)

    def act(self, env: EventSchedulingEnv, obs, mask: np.ndarray) -> int:
        valid = np.flatnonzero(mask)
        return int(self.rng.choice(valid))


class RuleBasedScheduler:
    """Greedy: among valid placements, maximize group-free ratio then venue fit."""
    name = "rule_based"

    def act(self, env: EventSchedulingEnv, obs, mask: np.ndarray) -> int:
        ev = env._current()
        free = env._free[(ev["department"], ev["semester"])]
        best, best_score = None, -np.inf
        for a in np.flatnonzero(mask):
            decoded = env.decode_action(int(a))
            if decoded is None:
                continue  # never defers
            d, s, v = decoded
            venue = env.venues[v]
            fill = min(1.0, ev["expected_audience"] / venue["capacity"])
            fit = 1.0 - abs(0.75 - fill)  # prefer ~75% expected fill
            score = 2.0 * free[d, s] + fit
            if score > best_score:
                best, best_score = int(a), score
        return best if best is not None else int(np.flatnonzero(mask)[0])


def run_episode(env: EventSchedulingEnv, scheduler, seed: int | None = None):
    """Roll one full semester; returns (total_reward, schedule_log)."""
    obs, info = env.reset(seed=seed)
    mask = info["action_mask"]
    total = 0.0
    done = False
    while not done:
        action = scheduler.act(env, obs, mask)
        obs, reward, done, _, info = env.step(action)
        total += reward
        mask = info.get("action_mask")
    return total, env.log
