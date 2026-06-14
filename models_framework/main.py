from storage import ModelStorage
from adapter import MistralAdapter, AnthropicAdapter, DeepSeekAdapter
from engine import QuestRunnerConcat, QuestRunnerChat, UI_CHECKPOINT
from config import CLAUDE_MODEL_NAME_HAIKU, CLAUDE_MODEL_NAME_SONNET, MISTRAL_MODEL_NAME, DEEPSEEK_MODEL_NAME_REASONER, SUMMARIZE_EASY, SUMMARIZE_HARD
from anthropic import APIError, RateLimitError, APITimeoutError
import time
from datetime import datetime


def safe_generate(adapter, user_prompt, system_prompt=None, temp=None, max_retries=30, base_delay=10.0):
    last_error = None

    for _ in range(max_retries):
        try:
            return adapter.generate(user_prompt, system_prompt, temperature=temp)

        except (RateLimitError, APITimeoutError, APIError, Exception) as e:
            last_error = e

            print(f"ERROR: {last_error}")

            sleep_time = base_delay
            time.sleep(sleep_time)

    print(f"LLM ERROR: Failed after {max_retries} retries: {last_error}")
    return ""


def update_summary(adapter, storage, summarize_type="hard"):

    old_summary = storage.data.get("summary", "")
    run_history = storage.data.get("current_run_history", "")

    if not run_history.strip():
        return
    
    user_prompt = f"""PREVIOUS SUMMARY:

{old_summary}

==========

LAST RUN HISTORY:

{run_history}"""
    
    summarize_prompt = SUMMARIZE_HARD if summarize_type == "hard" else SUMMARIZE_EASY

    new_summary = safe_generate(adapter, user_prompt, summarize_prompt)

    if new_summary.strip():
        storage.update_summary(new_summary)
        storage.clear_run_history()

    print(f"--- SUMMARY USER PROMPT:\n\n{user_prompt}\n\n--- SUMMARY NEW SUMMARY:\n\n{new_summary}\n\n")

    return new_summary


if __name__ == "__main__":

    start_time = time.time()

    # model_name = CLAUDE_MODEL_NAME_HAIKU
    # model_name = CLAUDE_MODEL_NAME_SONNET
    # model_name = MISTRAL_MODEL_NAME
    # model_name = DEEPSEEK_MODEL_NAME_REASONER

    # mode = "test"
    # mode = "chat"
    # mode = "concat"

    # temp = 0.2
    # temp = 0.0

    # lang = "ru"
    # lang = "en"

    # summarize_type = "easy"     # соответствует режиму short из текста
    # summarize_type = "hard"     # соответствует режиму full из текста



    if mode == "test":
        storage = ModelStorage(model_name="test", mode=mode, temp=temp, lang=lang, summarize_type=summarize_type)
    else:
        if model_name == CLAUDE_MODEL_NAME_HAIKU or model_name == CLAUDE_MODEL_NAME_SONNET:
            adapter = AnthropicAdapter(model_name=model_name, mode=mode)
        elif model_name == MISTRAL_MODEL_NAME:
            adapter = MistralAdapter(model_name=model_name, mode=mode)
        elif model_name == DEEPSEEK_MODEL_NAME_REASONER:
            adapter = DeepSeekAdapter(model_name=model_name, mode=mode)
        storage = ModelStorage(model_name=model_name, mode=mode, temp=temp, lang=lang, summarize_type=summarize_type)
    
    if mode == "concat":
        runner = QuestRunnerConcat(storage)
    else:
        runner = runner = QuestRunnerChat(storage)

    runner.start_quest()

    num_runs = 0
    num_iters = 0
    prev_runs = 0

    while num_runs < 90 and num_iters < 3000:

        if runner.finished:
            break

        if mode == "concat" and runner.ui_state == "ending":
            duration = time.time() - start_time
            storage.data["duration"] = duration
            storage._save()

        if mode == "chat" and runner.ui_state == "ending_cp":
            duration = time.time() - start_time
            storage.data["duration"] = duration
            storage._save()

        if mode != "test" and mode != "chat" and runner.ui_state == "ending":
            updated_summary = update_summary(adapter, storage, summarize_type=summarize_type)
            print(f"--------\n\nUPDATED_SUMMARY AFTER {new_runs} RUNS: {updated_summary}\n")
            runner.ui_state = UI_CHECKPOINT
            last_update_runs = new_runs

        output = runner.make_text()

        if mode == "test":
            print(output)
        else:
            answer = safe_generate(adapter, output + "\n\nAnswer with only one available option number. Your response must contain only the number, no explanations.", temp=temp)
            print(f"OUTPUT:\n\n{output}\n\nAnswer with only one available option number. Your response must contain only the number, no explanations.\n")
            print(f"ANSWER:\n\n{answer}\n")

        if mode == "test":
            choice = input("\n> ")
            print()
        else:
            choice = answer

        runner.handle_input(choice)

        new_runs = len(storage.data["runs"])

        num_runs = new_runs
        num_iters += 1
        
        print(f"--------\n\nITERS: {num_iters}\n\n")

        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        print(f"{'-' * 20} {timestamp}")
  