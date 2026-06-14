import json
from config import ENDINGS_PATH, QUEST_PATH, FIRST_SCENE_ID 

with open(QUEST_PATH, "r", encoding="utf-8") as f:
    QUEST_DATA = json.load(f)

with open(ENDINGS_PATH, "r", encoding="utf-8") as f:
    ENDINGS_DATA = json.load(f)

COUNT_ENDINGS = len(ENDINGS_DATA)

def get_scene_by_id(scene_id):
    for item in QUEST_DATA:
        if item["id"] == scene_id:
            return item
    return None

def get_choice_block(scene):
    target = scene.get("target")
    if target is None:
        return None

    next_item = get_scene_by_id(target)
    if next_item and next_item["type"] == "choice":
        return next_item

    return None


UI_SCENE = "scene"
UI_ENDING = "ending"
UI_CHECKPOINT = "checkpoint"
UI_FINISHED = "finished"


class QuestRunnerConcat:

    def __init__(self, storage):
        self.storage = storage

        self.ui_state = None

        self.finished = False

        self.last_screen = ""
        self.error_message = None

        self.lang = self.storage.data["lang"]


    def start_quest(self):
        self.storage.new_run(FIRST_SCENE_ID)

        self.storage.data["current_scene"] = FIRST_SCENE_ID

        self.storage.unlock_checkpoint(FIRST_SCENE_ID)

        self.finished = False

    def _check_error(self, text):
        if self.error_message is None:
            self.storage.update_conversation_log(text)
            self.storage.append_run_history(text)

        if self.error_message:
            msg = self.error_message
            self.error_message = None
            return msg + "\n\n" + text

        return text
    
    def make_text(self):
        new_text = self._render()

        if self.storage.mode == "chat":
            return new_text

        summary = self.storage.data.get("summary", "")

        if summary.strip():
            return (
                "SUMMARY:\n"
                + summary
                + "\n\n==========\n\n"
                + "CURRENT RUN:\n\n"
                + self.storage.data["current_run_history"]
            )

        return self.storage.data["conversation_log"]

    def _render(self):
        if self.finished:
            self.ui_state = UI_FINISHED
            self.last_screen = "The game is over. All endings are open."
            return self.last_screen

        scene_id = self.storage.data["current_scene"]

        if scene_id is None:
            self.ui_state = UI_CHECKPOINT
            self.last_screen = self._render_checkpoints()
            return self._check_error(self.last_screen)

        scene = get_scene_by_id(scene_id)

        if not scene:
            self.last_screen = "Error: scene not found."
            return self._check_error(self.last_screen)

        if scene["type"] == "scene":
            self.ui_state = UI_SCENE
            self.last_screen = self._render_scene(scene)
            return self._check_error(self.last_screen)

        if scene["type"] == "end":
            self.last_screen = self._render_ending(scene)
            return self._check_error(self.last_screen)

        self.last_screen = "Error: unknown scene type."
        return self._check_error(self.last_screen)
    

    def _render_scene(self, scene):
        text = scene["text"][self.lang]

        choice_block = get_choice_block(scene)

        out = ""

        cp_num = scene.get("checkpoint_num")

        if cp_num:
            out += f"CHECKPOINT {cp_num}. {scene.get('checkpoint_text')[self.lang]}\n\n"

        out += text + "\n"

        run = self.storage.data["current_run"]

        if len(run["scenes"]) > 1:
            out += "\n0. Go back"

        if choice_block:
            for b in choice_block["branches"]:
                out += f"\n{b['branch_id']}. {b['branch_text'][self.lang]}"

        return out


    def handle_input(self, player_input):
        player_input = player_input.strip()

        if self.finished:
            return None

        if self.ui_state == UI_SCENE:
            result = self._handle_scene_input(player_input)
            if self.error_message is None:
                choice_text = ("CHOICE: ") + player_input
                self.storage.update_conversation_log(choice_text)
                self.storage.append_run_history(choice_text)

                curr_scene = get_scene_by_id(self.storage.data["current_scene"])
                if curr_scene["type"] == "end":
                    self._render()
            else:
                self.storage.data["input_errors"].append(player_input)
                self.storage._save()
            return result

        if self.ui_state == UI_CHECKPOINT:
            result = self._handle_checkpoint(player_input)
            if self.error_message is None:
                choice_text = ("CHOICE: ") + player_input
                self.storage.update_conversation_log(choice_text)
                self.storage.append_run_history(choice_text)
            else:
                self.storage.data["input_errors"].append(player_input)
                self.storage._save()
            return result

        return None


    def _handle_scene_input(self, player_input):
        scene = get_scene_by_id(self.storage.data["current_scene"])

        if not scene:
            return None

        choice_block = get_choice_block(scene)

        if player_input == "0":
            run = self.storage.data["current_run"]
            if len(run["scenes"]) <= 1:
                return self._repeat()

            self._go_back()
            return None

        if not choice_block:
            return self._repeat()

        selected = None

        for b in choice_block["branches"]:
            if b["branch_id"] == player_input:
                selected = b
                break

        if selected is None:
            return self._repeat()

        self.storage.record_choice(
            selected["branch_id"],
            selected["target"]
        )

        self.storage.data["current_scene"] = selected["target"]

        self.storage.unlock_checkpoint(selected["target"])

        return None


    def _render_ending(self, scene):
        end_number = scene.get("number", "?")

        text = f"ENDING {end_number}\n\n{scene['text'][self.lang]}"

        self.storage.record_ending(end_number)

        endings_text = self.storage.data["endings_opened_text"]

        opened = self.storage.data["endings_opened"]
        count = len([k for k, v in opened.items() if v > 0])

        result = text + "\n\n" + endings_text

        self.storage.data["current_scene"] = None

        if count >= COUNT_ENDINGS:
            self.finished = True
            self.ui_state = UI_FINISHED
            return result + "\n\nAll endings are open."

        self.ui_state = UI_ENDING

        return result 
    

    def _render_checkpoints(self):

        return (
            self.storage.data["checkpoints_text"]
            + "\n\nChoose a checkpoint."
        )
    

    def _handle_checkpoint(self, player_input):
        checkpoints = self.storage.data["checkpoints"]

        cp = next(
            (c for c in checkpoints if str(c["num"]) == player_input),
            None
        )

        if not cp:
            return self._repeat()

        self.start_run(cp["scene_id"])

        return None


    def start_run(self, scene_id):
        self.storage.new_run(scene_id)

        self.storage.data["current_scene"] = scene_id

        self.storage.unlock_checkpoint(scene_id)

        self.ui_state = UI_SCENE


    def _go_back(self):
        self.storage.record_back()

        self.storage.data["current_scene"] = (
            self.storage.data["current_run"]["scenes"][-1]
        )

        self.storage.unlock_checkpoint(
            self.storage.data["current_scene"]
        )


    def _repeat(self):

        self.error_message = (
            "Selection error. Enter only the number of one of the available options."
        )






UI_ENDING_CP = "ending_cp"


class QuestRunnerChat:

    def __init__(self, storage):
        self.storage = storage

        self.ui_state = None

        self.finished = False

        self.last_screen = ""
        self.error_message = None

        self.lang = self.storage.data["lang"]


    def start_quest(self):
        self.storage.new_run(FIRST_SCENE_ID)

        self.storage.data["current_scene"] = FIRST_SCENE_ID

        self.storage.unlock_checkpoint(FIRST_SCENE_ID)

        self.finished = False


    def _check_error(self, text):
        if self.error_message is None:
            self.storage.update_conversation_log(text)
            self.storage.append_run_history(text)

        if self.error_message:
            msg = self.error_message
            self.error_message = None
            return msg + "\n\n" + text

        return text
    

    def make_text(self):
        new_text = self._render()

        if self.storage.mode == "chat":
            return new_text

        summary = self.storage.data.get("summary", "")

        if summary.strip():
            return (
                "SUMMARY:\n"
                + summary
                + "\n\n==========\n\n"
                + "CURRENT RUN:\n\n"
                + self.storage.data["current_run_history"]

            )

        return self.storage.data["conversation_log"]


    def _render(self):

        if self.finished:
            self.ui_state = UI_FINISHED
            self.last_screen = "The game is over. All endings are open."
            return self.last_screen
        
        scene_id = self.storage.data["current_scene"]

        if scene_id is None:
            self.ui_state = UI_ENDING_CP
            self.last_screen = self._render_checkpoints()
            return self._check_error(self.last_screen)

        scene = get_scene_by_id(scene_id)

        if not scene:
            self.last_screen = "Error: scene not found."
            return self._check_error(self.last_screen)

        if scene["type"] == "scene":
            self.ui_state = UI_SCENE
            self.last_screen = self._render_scene(scene)
            return self._check_error(self.last_screen)

        if scene["type"] == "end":
            self.last_screen = self._render_ending(scene)
            return self._check_error(self.last_screen)

        self.last_screen = "Error: unknown scene type."
        return self._check_error(self.last_screen)


    def _render_scene(self, scene):
        text = scene["text"][self.lang]

        choice_block = get_choice_block(scene)

        out = ""

        cp_num = scene.get("checkpoint_num")

        if cp_num:
            out += f"ЧЕКПОЙНТ {cp_num}. {scene.get('checkpoint_text')[self.lang]}\n\n"

        out += text + "\n"

        run = self.storage.data["current_run"]

        if len(run["scenes"]) > 1:
            out += "\n0. Go back"

        if choice_block:
            for b in choice_block["branches"]:
                out += f"\n{b['branch_id']}. {b['branch_text'][self.lang]}"

        return out


    def handle_input(self, player_input):
        player_input = player_input.strip()

        if self.finished:
            return None

        if self.ui_state == UI_SCENE:
            result = self._handle_scene_input(player_input)
            if self.error_message is None:
                choice_text = ("CHOICE: ") + player_input
                self.storage.update_conversation_log(choice_text)
                self.storage.append_run_history(choice_text)
            else:
                self.storage.data["input_errors"].append(player_input)
                self.storage._save()
            return result

        if self.ui_state == UI_ENDING_CP:
            result = self._handle_checkpoint(player_input)
            if self.error_message is None:
                choice_text = ("CHOICE: ") + player_input
                self.storage.update_conversation_log(choice_text)
                self.storage.append_run_history(choice_text)
            else:
                self.storage.data["input_errors"].append(player_input)
                self.storage._save()
            return result

        return None


    def _handle_scene_input(self, player_input):
        scene = get_scene_by_id(self.storage.data["current_scene"])

        if not scene:
            return None

        choice_block = get_choice_block(scene)

        if player_input == "0":
            run = self.storage.data["current_run"]
            if len(run["scenes"]) <= 1:
                return self._repeat()

            self._go_back()
            return None

        if not choice_block:
            return self._repeat()

        selected = None

        for b in choice_block["branches"]:
            if b["branch_id"] == player_input:
                selected = b
                break

        if selected is None:
            return self._repeat()

        self.storage.record_choice(
            selected["branch_id"],
            selected["target"]
        )

        self.storage.data["current_scene"] = selected["target"]

        self.storage.unlock_checkpoint(selected["target"])

        return None


    def _render_ending(self, scene):
        end_number = scene.get("number", "?")

        text = f"ENDING {end_number}\n\n{scene['text'][self.lang]}"

        self.storage.record_ending(end_number)

        endings_text = self.storage.data["endings_opened_text"]

        opened = self.storage.data["endings_opened"]
        count = len([k for k, v in opened.items() if v > 0])

        result = text + "\n\n" + endings_text

        self.storage.data["current_scene"] = None

        if count >= COUNT_ENDINGS:
            self.finished = True
            self.ui_state = UI_FINISHED
            return result + "\n\nAll endings are open."

        self.ui_state = UI_ENDING_CP

        return result + "\n\n" + self._render_checkpoints()


    def _render_checkpoints(self):

        return (
            self.storage.data["checkpoints_text"]
            + "\n\nChoose a checkpoint."
        )

    def _handle_checkpoint(self, player_input):
        checkpoints = self.storage.data["checkpoints"]

        cp = next(
            (c for c in checkpoints if str(c["num"]) == player_input),
            None
        )

        if not cp:
            return self._repeat()

        self.start_run(cp["scene_id"])

        return None


    def start_run(self, scene_id):

        self.storage.new_run(scene_id)

        self.storage.data["current_scene"] = scene_id

        self.storage.unlock_checkpoint(scene_id)

        self.ui_state = UI_SCENE


    def _go_back(self):
        self.storage.record_back()

        self.storage.data["current_scene"] = (
            self.storage.data["current_run"]["scenes"][-1]
        )

        self.storage.unlock_checkpoint(
            self.storage.data["current_scene"]
        )


    def _repeat(self):

        self.error_message = (
            "Selection error. Enter only the number of one of the available options."
        )