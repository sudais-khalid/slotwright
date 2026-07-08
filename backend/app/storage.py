"""Document store: MongoDB when MONGO_URL is set, JSON files otherwise.

Both backends expose the same three operations, so the rest of the code
never knows which one it is talking to (per the risk mitigation in PLAN.md).
Collections: students, events, venues, calendar, schedule_log, results.
"""
import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COLLECTIONS = ["students", "events", "venues", "calendar", "schedule_log", "results"]


class JsonStore:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        return self.data_dir / f"{name}.json"

    def replace_all(self, name: str, docs: list[dict]) -> None:
        self._path(name).write_text(json.dumps(docs, indent=1), encoding="utf-8")

    def load_all(self, name: str) -> list[dict]:
        p = self._path(name)
        if not p.exists():
            return []
        return json.loads(p.read_text(encoding="utf-8"))

    def append(self, name: str, docs: list[dict]) -> None:
        existing = self.load_all(name)
        existing.extend(docs)
        self.replace_all(name, existing)


class MongoStore:
    def __init__(self, url: str, db_name: str = "event_scheduler"):
        from pymongo import MongoClient
        self.db = MongoClient(url, serverSelectionTimeoutMS=3000)[db_name]
        self.db.client.admin.command("ping")  # fail fast if unreachable

    def replace_all(self, name: str, docs: list[dict]) -> None:
        self.db[name].delete_many({})
        if docs:
            self.db[name].insert_many([dict(d) for d in docs])

    def load_all(self, name: str) -> list[dict]:
        return list(self.db[name].find({}, {"_id": 0}))

    def append(self, name: str, docs: list[dict]) -> None:
        if docs:
            self.db[name].insert_many([dict(d) for d in docs])


DEFAULT_MONGO_URL = "mongodb://localhost:27017"


def get_store():
    url = os.environ.get("MONGO_URL", DEFAULT_MONGO_URL)
    try:
        store = MongoStore(url)
        print(f"[storage] using MongoDB at {url}")
        return store
    except Exception as exc:  # unreachable Mongo -> JSON fallback
        print(f"[storage] MongoDB unavailable ({exc}); falling back to JSON store")
        return JsonStore()
