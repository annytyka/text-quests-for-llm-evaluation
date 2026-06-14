import json
import os
import asyncio

class UserStorage:
    def __init__(self, base_path: str):
        self.base_path = base_path
        self._locks = {}

        os.makedirs(self.base_path, exist_ok=True)

    def _get_path(self, username: str):
        return os.path.join(self.base_path, f"{username}.json")

    def _get_lock(self, username: str):
        if username not in self._locks:
            self._locks[username] = asyncio.Lock()
        return self._locks[username]

    async def get_user(self, username: str):
        lock = self._get_lock(username)

        async with lock:
            path = self._get_path(username)

            if not os.path.exists(path):
                return None

            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    async def create_user(self, username: str, data: dict):
        lock = self._get_lock(username)

        async with lock:
            path = self._get_path(username)

            if os.path.exists(path):
                return

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    async def update_user(self, username: str, update_fn):
        lock = self._get_lock(username)

        async with lock:
            path = self._get_path(username)

            if not os.path.exists(path):
                return None

            with open(path, "r", encoding="utf-8") as f:
                user = json.load(f)

            update_fn(user)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(user, f, ensure_ascii=False, indent=2)

            return user


class UserIndex:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def _load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_user(self, username: str, user_alias: str, users_counter: int):
        data = self._load()
        data[username] = {
            "user_alias": user_alias or "unknown",
            "users_counter": users_counter
        }
        self._save(data)

    def get_user_alias(self, username: str):
        data = self._load()
        return data.get(username)

    def get_all(self):
        return self._load()

    def exists(self, username: str):
        data = self._load()
        return username in data
