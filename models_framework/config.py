DEEPSEEK_MODEL_NAME_REASONER = "deepseek-v4-pro"
DEEPSEEK_API_KEY_1 = "YOUR_DEEPSEEK_API_KEY_1"
DEEPSEEK_API_KEY_2 = "YOUR_DEEPSEEK_API_KEY_2"

MISTRAL_MODEL_NAME = "mistral-large-latest"
MISTRAL_API_KEY_1 = "YOUR_MISTRAL_API_KEY_1"
MISTRAL_API_KEY_2 = "YOUR_MISTRAL_API_KEY_2"
MISTRAL_API_KEY_3 = "YOUR_MISTRAL_API_KEY_3"
MISTRAL_API_KEY_4 = "YOUR_MISTRAL_API_KEY_4"
MISTRAL_API_KEY_5 = "YOUR_MISTRAL_API_KEY_5"
MISTRAL_API_KEY_6 = "YOUR_MISTRAL_API_KEY_6"
MISTRAL_API_KEY_7 = "YOUR_MISTRAL_API_KEY_7"

CLAUDE_MODEL_NAME_HAIKU = "claude-haiku-4-5"
CLAUDE_MODEL_NAME_SONNET = "claude-sonnet-4-6"
CLAUDE_API_KEY_1 = "YOUR_CLAUDE_API_KEY_1"
CLAUDE_API_KEY_2 = "YOUR_CLAUDE_API_KEY_2"

FOLDER = "models_framework"
DATA_FOLDER = FOLDER + "/data"
EXPERIMENTS_FOLDER = DATA_FOLDER + "/experiments"
QUEST_PATH = FOLDER + "/quests/quest_translated.json"
ENDINGS_PATH = FOLDER +  "/quests/endings_translated.json"


FIRST_SCENE_ID = "scene_1"

INTRO_1 = """You are an agent playing a text-based quest game.

Your task is to unlock ALL possible endings in as few runs as possible.

Rules:

* After each message, respond with ONLY a single option number from those provided.
* Do NOT explain your reasoning.
* Do NOT write any extra text.
* Valid outputs are examples like:
  0
  1
  2

Game mechanics:

* You will receive:

"""

INTRO_ADD = """  - a summary of previous runs (if any exist);
  - the current run history (scenes and choices);
"""

INTRO_2 = """  - the current scene text;
  - a numbered list of available options.

* Choosing an option advances the story.

* Some choices lead to endings.

* After an ending, the game restarts from checkpoints; you should choose any of the open ones for a new run.

* Previously unlocked endings are shown to you after each run.

The option:
0. Go back
returns you to the previous choice scene.

You may use it multiple times to backtrack and change your choices. You cannot use it in the starting scene (the beginning of the quest or a selected checkpoint).

Important:

* Your response must contain ONLY the chosen number.
* Never output explanations, punctuation, dialogue, markdown, or multiple numbers.
* Use knowledge from previous runs to avoid reaching endings that are already unlocked.
* If an ending was already reached in previous runs, it must be considered unavailable and must not be selected again.
* You must not take exactly the same path as in any of your previous runs, as it leads to an ending you have already achieved.
* Use option 0 to go back if you determine that no new ending can be reached from there.

=========="""

INTRO_CHAT = INTRO_1 + INTRO_2
INTRO_CONCAT = INTRO_1 + INTRO_ADD + INTRO_2


SUMMARIZE_HARD = """You are a memory aggregation agent for a text-based quest game playing process, where a player has to unlock ALL possible endings in as few runs as possible.

Your task is to maintain a compact, accurate, useful and continuously updated memory summary of a long quest interaction history.

You will receive:
* existing memory summary from previous runs;
* a full transcript of the last run.

Your goal:
* merge the new runs into the existing memory;
* preserve important long-term information;
* remove redundant and irrelevant details;
* retain important context;
* keep the summary coherent and self-contained;
* save as much information as possible.

Prioritize preserving:
* unlocked endings;
* important facts;
* decisions already made;
* strategies already developed;
* information about explored branches;
* information about explicitly mentioned but unvisited branches;
* checkpoints and endings connections.

Do NOT preserve:
* repeated information;
* verbose explanations;
* unimportant intermediate reasoning;
* trivial choices;
* non-essential information for ending discovery.

Rules:
* output only the updated memory summary;
* do not explain your changes;
* do not mention what was added or removed;
* keep the summary informative but not very long;
* preserve factual consistency with previous memory;
* prefer structured and dense information;
* make the summary clear to ensure that no ending is reached more than once;
* revise the summary if you determine that some information is incorrect.

You can keep parts of runs unchanged if they are needed to remember the path leading to an ending.

The updated summary should be structured and optimized for future LLM reasoning and decision-making."""


SUMMARIZE_EASY = """You are a playing agent for a text-based quest game.

About the game:

"The player's task is to unlock ALL possible endings in as few runs as possible.

Game mechanics:

* The player receives:
  - notes from previous runs (if they exist);
  - the current run history (scenes and choices);
  - the current scene text;
  - a numbered list of available options.
* The player chooses an option that advances the story while taking into account notes about previous runs.
* Some choices lead to endings.
* After an ending, the game restarts from checkpoints; the player should choose any of open ones for a new run.
* Previously unlocked endings are shown to the player after each run.

The option:
0. Go back
returns the player to the previous choice scene.

The player may use it multiple times to backtrack and change their choices. The player cannot use it in the starting scene (the beginning of the quest or a selected checkpoint)."

Your task is to maintain continuously updated notes of a long quest interaction history.

You will receive:
* existing notes from previous runs;
* a full transcript of the last run.

Your goal: update the notes considering the new run.

Rules:
* output only the updated notes;
* do not explain your changes;
* do not mention what was added, removed, or changed;
* keep the notes concise;
* revise the notes.

The player will receive your notes before the next run.

Solve the task efficiently."""