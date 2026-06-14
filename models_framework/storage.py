import os
import json
from datetime import datetime
from config import EXPERIMENTS_FOLDER, ENDINGS_PATH, QUEST_PATH, FIRST_SCENE_ID

with open(QUEST_PATH, "r", encoding="utf-8") as f:
    QUEST_DATA = json.load(f)

with open(ENDINGS_PATH, "r", encoding="utf-8") as f:
    ENDINGS_DATA = json.load(f)

def get_ending_description(ending_id: str, endings_data, lang):
        for e in endings_data:
            if e["id"] == ending_id:
                return e["text"][lang]
        return "???"

def build_endings_text(opened, endings_data, lang):
    count = len([id for id, counter in opened.items() if counter > 0])

    count_text = f"You have unlocked {count} out of {len(opened)} possible endings!\n\n"

    text = "UNLOCKED ENDINGS\n\n"

    lines = []

    for i in range(1, len(opened) + 1):
        num = str(i)

        if opened[num] > 0:
            desc = get_ending_description(num, endings_data, lang)
            lines.append(f"{i} — {desc}")
        else:
            lines.append(f"{i} — ✕")

    full_text = count_text + text + "\n".join(lines)

    return full_text

def get_scene_by_id(scene_id):
    for item in QUEST_DATA:
        if item["id"] == scene_id:
            return item
    return None

def build_checkpoints_text(checkpoints):
    if not checkpoints:
        return ""

    text = "AVAILABLE CHECKPOINTS"
    for cp in checkpoints:
        cp_text = str(cp["num"]) + ". " + cp["text"]
        text += "\n\n" + cp_text

    return text


class ModelStorage:
    def __init__(self, model_name="default", mode="concat", temp=0.0, lang="ru", summarize_type="hard", data_dir=EXPERIMENTS_FOLDER):
        
        self.model_name = model_name
        self.mode = mode
        self.lang = lang
        self.endings_data = ENDINGS_DATA

        self.model_dir = os.path.join(data_dir, model_name)
        os.makedirs(self.model_dir, exist_ok=True)
        self.model_mode_dir = os.path.join(self.model_dir, mode)
        os.makedirs(self.model_mode_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")

        self.session_path = os.path.join(
            self.model_mode_dir,
            f"session_{timestamp}_{lang}_{summarize_type}.json"
        )

        endings_opened = {e["id"]: 0 for e in self.endings_data}

        self.data = {
            "model": model_name,
            "mode": mode,
            "temp": temp,
            "lang": lang,
            "summarize_type": summarize_type,
            "started_at": timestamp,

            "run_counter": 0,
            "current_scene": None,

            "current_run": {
                "choices": [],
                "scenes": [],
                "ending": None,
                "choices_history": [],
                "scenes_history": []
            },
            "runs": [],

            "endings_opened": endings_opened,
            "endings_history": [],

            "checkpoints": [],

            "input_errors": [],

            "conversation_log": "",

            "endings_opened_text": build_endings_text(endings_opened, self.endings_data, self.lang),

            "checkpoints_text": None,

            "summary": "",
            "summaries_history": [],
            "current_run_history": ""
        }

        self._save()


    def _save(self):
        with open(self.session_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _update_endings_text(self):
        self.data["endings_opened_text"] = build_endings_text(self.data["endings_opened"], self.endings_data, self.lang)

    def _update_checkpoints_text(self):
        self.data["checkpoints_text"] = build_checkpoints_text(self.data["checkpoints"])

    def update_conversation_log(self, text):
        old_log = self.data.get("conversation_log", "")

        if old_log:
            self.data["conversation_log"] = (
                old_log + "\n\n" + text
            )
        else:
            self.data["conversation_log"] = text

        self._save()

    def append_run_history(self, text):
        old = self.data.get("current_run_history", "")

        if old:
            self.data["current_run_history"] = old + "\n\n" + text
        else:
            self.data["current_run_history"] = text

        self._save()

    def clear_run_history(self):
        self.data["current_run_history"] = ""
        self._save()

    def update_summary(self, text):
        run_num = self.data["run_counter"]

        if run_num:
            self.data["summaries_history"].append({
                "run": run_num - 1,
                "summary": self.data.get("summary", "").strip()
            })

        self.data["summary"] = text

        self._save()


    def record_choice(self, choice_id, next_scene_id):
        run = self.data.get("current_run")

        if not run:
            return

        run["choices"].append(choice_id)
        run["scenes"].append(next_scene_id)
        run["choices_history"].append(choice_id)
        run["scenes_history"].append(next_scene_id)

        self.data["current_run"] = run

        self.data["current_scene"] = next_scene_id

        self._save()


    def record_back(self):
        run = self.data.get("current_run")

        if not run:
            return

        run["choices"].pop()
        run["scenes"].pop()
        prev_scene_id = run["scenes"][-1]
        run["choices_history"].append("0")
        run["scenes_history"].append(prev_scene_id)

        self.data["current_run"] = run

        self.data["current_scene"] = prev_scene_id
        
        self._save()


    def record_ending(self, end_number):
        run = self.data.get("current_run")

        if run:
            run.setdefault("ending", None)
            run["ending"] = end_number

        self.data["current_run"] = run

        self.data.setdefault("endings_history", [])
        self.data["endings_history"].append(end_number)

        self.data.setdefault("endings_opened", {})
        self.data["endings_opened"].setdefault(end_number, 0)
        self.data["endings_opened"][end_number] += 1

        if run:
            self.data.setdefault("runs", [])
            run_with_id = run.copy()
            run_with_id["run_id"] = self.data["run_counter"]
            self.data["runs"].append(run_with_id)

        self.data["current_run"] = {
                "choices": [],
                "scenes": [],
                "ending": None,
                "choices_history": [],
                "scenes_history": []
            }
        self.data["current_scene"] = None

        self._update_endings_text()

        self._save()


    def new_run(self, scene_id=None):
        if scene_id is None:
            scene_id = FIRST_SCENE_ID

        self.data["current_run"] = {
            "choices": [],
            "scenes": [scene_id],
            "ending": None,
            "choices_history": [],
            "scenes_history": [scene_id]
        }

        self.data["current_scene"] = scene_id
        self.data["run_counter"] += 1

        self._save()

        return


    def unlock_checkpoint(self, scene_id):
        scene = get_scene_by_id(scene_id)

        if not scene:
            return

        if scene.get("checkpoint_num") is None:
            return

        checkpoint = {
            "num": scene["checkpoint_num"],
            "text": scene["checkpoint_text"][self.lang],
            "scene_id": scene["id"]
        }

        self.data.setdefault("checkpoints", [])

        if not any(c["num"] == checkpoint["num"] for c in self.data["checkpoints"]):
            self.data["checkpoints"].append(checkpoint)

        self._update_checkpoints_text()

        self._save()
