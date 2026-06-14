import json
from aiogram.types import Message


class QuestEngine:

    def __init__(self, path):

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.nodes = {node["id"]: node for node in data}

        self.current = data[0]["id"]

        self.choices = []

    def get_node(self):

        return self.nodes[self.current]

    def is_scene(self):

        return self.get_node()["type"] == "scene"

    def is_choice(self):

        return self.get_node()["type"] == "choice"

    def get_scene_text(self):

        node = self.get_node()

        if node["type"] != "scene":
            return None

        return node["text"]

    def get_branches(self):

        node = self.get_node()

        if node["type"] != "choice":
            return []

        return node["branches"]

    def go_next_from_scene(self):

        node = self.get_node()

        if "target" not in node:
            return False

        self.current = node["target"]

        return True

    def choose(self, index):

        node = self.get_node()

        branches = node["branches"]

        branch = branches[index]

        self.choices.append(branch["branch_id"])

        self.current = branch["target"]

    def is_dead_end(self):

        node = self.get_node()

        if node["type"] == "scene" and "target" not in node:
            return True

        if node["type"] == "choice" and len(node["branches"]) == 0:
            return True

        return False


async def safe_delete(message: Message):
    try:
        await message.delete()
    except:
        pass