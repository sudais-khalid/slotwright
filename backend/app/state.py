"""In-process application state: dataset, trained agent, and training progress.

Training runs in a daemon thread; TrainingState is the single source of truth
the REST status endpoint and the WebSocket both read from.

Dataset shape metadata (days/slots/weeks/departments/semesters/source) rides
alongside the five FR-defined collections in a "meta" document, since the
Gymnasium env needs it but it isn't itself one of the doc's NoSQL collections.
"""
import threading
from pathlib import Path

from rl.env import EventSchedulingEnv
from rl.q_learning import MODELS_DIR, QLearningAgent
from simulator.generators import generate_dataset
from simulator.import_real import import_real_dataset

from .storage import get_store

REAL_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "real_data"
DATASET_KEYS = ("students", "events", "venues", "calendar")
META_KEYS = ("days", "slots", "weeks", "departments", "semesters", "source", "seed")


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


def _has_real_files() -> bool:
    if not REAL_DATA_DIR.exists():
        return False
    return all(any((REAL_DATA_DIR / d).glob("*.pdf")) for d in ("timetables", "venues", "events"))


class AppState:
    def __init__(self):
        self.store = get_store()
        self.training = TrainingState()
        self.agent: QLearningAgent | None = None
        self.dataset: dict | None = None
        self.import_error: str | None = None
        self._load_or_generate()

    # ---------- persistence ----------
    def _persist_dataset(self):
        for name in DATASET_KEYS:
            self.store.replace_all(name, self.dataset[name])
        self.store.replace_all("meta", [{k: self.dataset[k] for k in META_KEYS}])
        self.store.replace_all("schedule_log", [])

    def _load_or_generate(self):
        students = self.store.load_all("students")
        meta_docs = self.store.load_all("meta")
        if students and meta_docs:
            self.dataset = {k: self.store.load_all(k) for k in DATASET_KEYS}
            self.dataset.update({k: meta_docs[0][k] for k in META_KEYS})
        elif _has_real_files():
            self.load_real_data()
        else:
            self.regenerate(seed=42)
        qpath = MODELS_DIR / "q_table.pkl"
        if qpath.exists():
            self.agent = QLearningAgent.load(qpath)

    # ---------- dataset switching ----------
    def regenerate(self, seed: int = 42, n_students: int = 480, n_events: int = 40) -> dict:
        self.dataset = generate_dataset(seed=seed, n_students=n_students, n_events=n_events)
        self._persist_dataset()
        self.agent = None  # stale policy no longer matches the data
        return self._counts()

    def load_real_data(self) -> dict:
        self.dataset = import_real_dataset(REAL_DATA_DIR)
        self._persist_dataset()
        self.agent = None
        self.import_error = None
        return self._counts()

    def _counts(self) -> dict:
        return {name: len(self.dataset[name]) for name in DATASET_KEYS}

    def save_uploaded_file(self, kind: str, filename: str, content: bytes) -> Path:
        if kind not in ("timetables", "venues", "events"):
            raise ValueError(f"Unknown upload kind '{kind}'")
        target_dir = REAL_DATA_DIR / kind
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / filename
        path.write_bytes(content)
        return path

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
