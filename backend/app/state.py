"""In-process application state: dataset, trained agent, and training progress.

Training runs in a daemon thread; TrainingState is the single source of truth
the REST status endpoint and the WebSocket both read from.
"""
import threading

from rl.env import EventSchedulingEnv
from rl.q_learning import MODELS_DIR, QLearningAgent
from simulator.generators import generate_dataset

from .storage import get_store


class TrainingState:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.episode = 0
        self.total_episodes = 0
        self.rewards: list[float] = []
        self.error: str | None = None

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "running": self.running,
                "episode": self.episode,
                "total_episodes": self.total_episodes,
                "rewards": list(self.rewards),
                "avg_reward_last_50": (
                    round(sum(self.rewards[-50:]) / min(50, len(self.rewards)), 2)
                    if self.rewards else None
                ),
                "error": self.error,
            }


class AppState:
    def __init__(self):
        self.store = get_store()
        self.training = TrainingState()
        self.agent: QLearningAgent | None = None
        self.dataset: dict | None = None
        self._load_or_generate()

    def _load_or_generate(self):
        students = self.store.load_all("students")
        if students:
            self.dataset = {
                "students": students,
                "events": self.store.load_all("events"),
                "venues": self.store.load_all("venues"),
                "calendar": self.store.load_all("calendar"),
            }
        else:
            self.regenerate(seed=42)
        qpath = MODELS_DIR / "q_table.pkl"
        if qpath.exists():
            self.agent = QLearningAgent.load(qpath)

    def regenerate(self, seed: int = 42, n_students: int = 480, n_events: int = 40) -> dict:
        self.dataset = generate_dataset(seed=seed, n_students=n_students, n_events=n_events)
        for name in ("students", "events", "venues", "calendar"):
            self.store.replace_all(name, self.dataset[name])
        self.store.replace_all("schedule_log", [])
        self.agent = None  # stale policy no longer matches the data
        return {name: len(self.dataset[name]) for name in ("students", "events", "venues", "calendar")}

    def start_training(self, episodes: int, alpha: float, gamma: float) -> bool:
        ts = self.training
        with ts.lock:
            if ts.running:
                return False
            ts.running, ts.episode, ts.total_episodes = True, 0, episodes
            ts.rewards, ts.error = [], None

        def _run():
            try:
                env = EventSchedulingEnv(self.dataset, seed=0)
                agent = QLearningAgent(n_actions=env.action_space.n, alpha=alpha, gamma=gamma, seed=0)

                def on_episode(ep, reward):
                    with ts.lock:
                        ts.episode = ep + 1
                        ts.rewards.append(round(reward, 2))

                agent.train(env, episodes=episodes, on_episode=on_episode)
                agent.save()
                self.agent = agent
            except Exception as exc:
                with ts.lock:
                    ts.error = str(exc)
            finally:
                with ts.lock:
                    ts.running = False

        threading.Thread(target=_run, daemon=True).start()
        return True


state = AppState()
