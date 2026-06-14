import json
import time
from mistralai import Mistral
MISTRAL_API_KEY_1 = "YOUR_MISTRAL_API_KEY_1"
MISTRAL_API_KEY_2 = "YOUR_MISTRAL_API_KEY_2"


FOLDER = "models_framework"
QUEST_PATH = FOLDER + "/quests/basics/quest.json"
ENDINGS_PATH = FOLDER +  "/quests/basics/endings.json"

NEW_QUEST_PATH = FOLDER + "/quests/quest_translated.json"
NEW_ENDINGS_PATH = FOLDER +  "/quests/endings_translated.json"

quest_path = QUEST_PATH
translated_quest_path = NEW_QUEST_PATH

endings_path = ENDINGS_PATH
translated_endings_path = NEW_ENDINGS_PATH


clients = [
    Mistral(
        api_key=MISTRAL_API_KEY_1,
        timeout_ms=10000
    ),
    Mistral(
        api_key=MISTRAL_API_KEY_2,
        timeout_ms=10000
    )
]

client_index = 0


def get_next_client():
    global client_index

    client = clients[client_index]

    client_index = (client_index + 1) % len(clients)

    return client


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def translate(text: str, target_lang: str) -> str:

    if target_lang != "en":
        raise ValueError(f"Unknown language: {target_lang}")

    prompt = f"""Translate the following Russian text into English while carefully considering the contextual meaning and possible ambiguity of words:

{text}

Preserve the original meaning, tone, formatting, punctuation, line breaks, and dialogue structure.

Surround em dashes with spaces.

Do not wrap the entire translation in quotation marks.

Do not add any additional comments, explanations, notes, clarifications, or remarks.

Return ONLY the translated text!"""

    last_error = None

    for attempt in range(10):

        try:

            client = get_next_client()

            res = client.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.0,
                max_tokens=1024,
            )

            translated = res.choices[0].message.content.strip()

            time.sleep(0.5)

            return translated

        except (RateLimitError, APITimeoutError, APIError, Exception) as e:

            last_error = e

            print(f"ERROR: {e}")

            sleep_time = min(30, 2 * attempt)

            print(f"SLEEP {sleep_time}s")

            time.sleep(sleep_time)

    raise RuntimeError(f"Translation failed: {last_error}")


def translate_text_field(value):

    if isinstance(value, dict):
        return value

    return {
        "ru": value,
        "en": translate(value, "en")
    }


def add_translations(input_path: str, output_path: str):

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for _, node in enumerate(data):

        try:

            if "text" in node:
                node["text"] = translate_text_field(node["text"])

            if "checkpoint_text" in node:
                node["checkpoint_text"] = translate_text_field(
                    node["checkpoint_text"]
                )

            if node.get("type") == "choice" and "branches" in node:

                for branch in node["branches"]:

                    if "branch_text" in branch:
                        branch["branch_text"] = translate_text_field(
                            branch["branch_text"]
                        )

            save_json(data, output_path)

        except Exception as e:

            print(f"FAILED NODE: {node.get('id')}")
            print(e)

            save_json(data, output_path)


add_translations(
    quest_path,
    translated_quest_path
)


add_translations(
    endings_path,
    translated_endings_path
)

