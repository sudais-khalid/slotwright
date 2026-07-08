"""Tabular Q-Learning agent with action masking (FR-06).

The coarse MultiDiscrete observation is used directly as the Q-table key
(324 states x 241 actions worst case, stored sparsely in a dict).
"""
import pickle
from collections import defaultdict
from pathlib import Path

import numpy as np

from .env import EventSchedulingEnv

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


class QLearningAgent:
    name = "rl"

    def __init__(self, n_actions: int, alpha: float = 0.1, gamma: float = 0.4,
                 epsilon: float = 1.0, epsilon_min: float = 0.05,
                 epsilon_decay: float = 0.995, seed: int = 0):
        self.n_actions = n_actions
        self.alpha, self.gamma = alpha, gamma
        self.epsilon, self.epsilon_min, self.epsilon_decay = epsilon, epsilon_min, epsilon_decay
        self.q = defaultdict(lambda: np.zeros(self.n_actions))
        self.rng = np.random.default_rng(seed)

    @staticmethod
    def _key(obs) -> tuple:
        return tuple(int(x) for x in obs)

    def act(self, env: EventSchedulingEnv, obs, mask: np.ndarray, greedy: bool = True) -> int:
        valid = np.flatnonzero(mask)
        if not greedy and self.rng.random() < self.epsilon:
            return int(self.rng.choice(valid))
        qvals = self.q[self._key(obs)][valid]
        return int(valid[int(np.argmax(qvals))])

    def update(self, obs, action: int, reward: float, next_obs, next_mask, done: bool):
        key = self._key(obs)
        if done or next_mask is None:
            target = reward
        else:
            valid = np.flatnonzero(next_mask)
            target = reward + self.gamma * float(np.max(self.q[self._key(next_obs)][valid]))
        self.q[key][action] += self.alpha * (target - self.q[key][action])

    def train(self, env: EventSchedulingEnv, episodes: int = 500,
              on_episode=None) -> list[float]:
        """Returns per-episode total reward. `on_episode(i, reward)` is called
        after each episode — the API layer uses it to stream live progress."""
        history = []
        for ep in range(episodes):
            obs, info = env.reset(seed=ep)
            mask = info["action_mask"]
            total, done = 0.0, False
            while not done:
                action = self.act(env, obs, mask, greedy=False)
                next_obs, reward, done, _, info = env.step(action)
                next_mask = info.get("action_mask")
                self.update(obs, action, reward, next_obs, next_mask, done)
                obs, mask, total = next_obs, next_mask, total + reward
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
            history.append(total)
            if on_episode:
                on_episode(ep, total)
        return history

    # ---------- persistence ----------
    def save(self, path: Path | None = None) -> Path:
        path = path or MODELS_DIR / "q_table.pkl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"q": dict(self.q), "n_actions": self.n_actions}, f)
        return path

    @classmethod
    def load(cls, path: Path | None = None) -> "QLearningAgent":
        path = path or MODELS_DIR / "q_table.pkl"
        with open(path, "rb") as f:
            blob = pickle.load(f)
        agent = cls(n_actions=blob["n_actions"], epsilon=0.0)
        for k, v in blob["q"].items():
            agent.q[k] = v
        return agent
