from collections import defaultdict
from statistics import mean
import json
import os
import pandas as pd
import numpy as np


QUEST_PATH = "models_framework/quests/basics/quest.json"
ENDINGS_PATH = "models_framework/quests/basics/endings.json"
FIRST_SCENE_ID = "scene_1"
MODELS_FOLDER = "data_models_full/"
USERS_FOLDER = "data_users_full/"
METRICS_FOLDER_BASE = "metrics/"
METRICS_FOLDER = METRICS_FOLDER_BASE + "counted/"
SERVICE_INFO_PATH = METRICS_FOLDER_BASE + "service_info.json"
RESULTS_FILE_PATH = METRICS_FOLDER_BASE + "results.json"
TABLE_FILE_PATH = METRICS_FOLDER_BASE + "results.xlsx"


def load_json(path, encoding="utf-8"):
    with open(path, "r", encoding=encoding) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


endings_info = load_json(SERVICE_INFO_PATH)

checkpoints = defaultdict(set)

for ending, info in endings_info.items():
    cp = info["checkpoint_num"]
    checkpoints[cp].add(ending)


total_average_depth = mean(
    info["depth_from_start"]
    for info in endings_info.values()
)


def safe_mean(xs):
    xs = [x for x in xs if x is not None]
    return mean(xs) if xs else 0.0


def count_back_steps(history, back_token="0"):
    return sum(1 for x in history if x == back_token)


def min_full_run_lengths_by_ending(runs):
    result = {}

    for run in runs:

        ending = run.get("ending")

        if ending is None:
            continue

        full_run = run.get("full_run", [])

        if full_run == []:
            full_run = run.get("scenes", [])

        run_len = len(full_run) - 1

        if (
            ending not in result
            or run_len < result[ending]
        ):
            result[ending] = run_len

    return result


def metric_finding_fraction(runs, q=0.5):
    first_found = {}

    for idx, run in enumerate(runs, start=1):

        ending = run.get("ending")

        if ending is not None and ending not in first_found:
            first_found[ending] = idx

    values = list(first_found.values())

    if not values:
        return None

    return float(np.quantile(values, q))


def metric_iteration_to_n_endings(runs, n):
    seen = set()

    for idx, run in enumerate(runs, start=1):

        ending = run.get("ending")

        if ending is None:
            continue

        seen.add(ending)

        if len(seen) >= n:
            return idx

    return None


def compute_metrics(data):
    runs = data["runs"]

    endings_opened = data["endings_opened"]

    endings_opened_counts = [e for e in endings_opened.values() if e > 0]

    metrics = {}

    metrics["RunCounter"] = len(runs)

    metrics["StepsCounter"] = sum([len(run["choices_history"]) for run in runs])

    metrics["UniqueEndings"] = len(endings_opened_counts) / len(endings_info)

    metrics["Fullness"] = [mean([1 if endings_opened[e] > 0 else 0 for e in ch]) for ch in checkpoints.values()]

    metrics["BadRuns"] = 1 - len(endings_opened_counts) / len(runs)

    metrics["RepeatEndings"] = mean(endings_opened_counts)

    opened_endings = {
        run["ending"]
        for run in runs
        if run.get("ending") is not None
    }

    depths = [
        endings_info[e]["depth_from_start"]
        for e in opened_endings
        if e in endings_info
    ]

    average_depth = mean(depths) if depths else 0.0

    metrics["AverageDepth"] = average_depth / total_average_depth

    backs_count = sum(
        x == "0"
        for run in runs
        for x in run.get("choices_history", [])
    )

    metrics["TotalBack"] = backs_count / sum(
        len(run.get("choices_history", []))
        for run in runs
    )

    chains = []
    for run in runs:
        history = run.get(
            "choices_history",
            []
        )
        cur = 0
        for x in history:
            if x == "0":
                cur += 1
            else:
                if cur > 0:
                    chains.append(cur)
                cur = 0
        if cur > 0:
            chains.append(cur)

    metrics["AverageBackLength"] = mean(chains) if chains else None

    useless = 0
    valid_backs = 0

    for run in runs:

        choices = run.get(
            "choices_history",
            []
        )

        scenes = run.get(
            "scenes_history",
            []
        )

        tried = {}

        for i in range(len(choices)):

            choice = choices[i]

            if i >= len(scenes):
                break

            scene = scenes[i]

            if choice == "0":

                if i + 1 >= len(choices):
                    continue

                next_choice = choices[i + 1]

                if next_choice == "0":
                    continue
                else:
                    valid_backs += 1

                if i + 1 >= len(scenes):
                    continue

                next_scene = scenes[i + 1]

                if (
                    next_scene in tried
                    and next_choice in tried[next_scene]
                ):
                    useless += 1

                continue

            tried.setdefault(scene, set()).add(choice)

    metrics["RedundantBacks"] = useless / valid_backs if valid_backs > 0 else None

    metrics["Finding50"] = (
        metric_finding_fraction(
            runs,
            0.5
        )
    )

    metrics["Finding90"] = (
        metric_finding_fraction(
            runs,
            0.9
        )
    )

    metrics["Finding100"] = (
        metric_finding_fraction(
            runs,
            1.0
        )
    )

    metrics["Iteration20"] = (
        metric_iteration_to_n_endings(
            runs,
            20
        )
    )

    metrics["Iteration27"] = (
        metric_iteration_to_n_endings(
            runs,
            27
        )
    )

    metrics["Iteration28"] = (
        metric_iteration_to_n_endings(
            runs,
            28
        )
    )

    metrics["Iteration29"] = (
        metric_iteration_to_n_endings(
            runs,
            29
        )
    )

    metrics["Iteration30"] = (
        metric_iteration_to_n_endings(
            runs,
            30
        )
    )

    return metrics



def count_models_metrics():
    os.makedirs(METRICS_FOLDER, exist_ok=True)

    for subdir in os.listdir(MODELS_FOLDER):
        old_subdir = os.path.join(MODELS_FOLDER, subdir)
        if not os.path.isdir(old_subdir):
            continue
        for filename in os.listdir(old_subdir):

            if not filename.endswith(".json"):
                continue

            src_path = os.path.join(
                old_subdir,
                filename
            )

            model_data = load_json(src_path)

            metrics = compute_metrics(
                model_data
            )

            model = model_data.get("model", "unknown")
            mode = model_data.get("mode", "unknown")
            lang = model_data.get("lang", "unknown")
            summarize_type = model_data.get("summarize_type", "unknown")

            out_name = (
                f"{model}_{mode}_{lang}_{summarize_type}.json"
            )

            out_path = os.path.join(
                METRICS_FOLDER,
                out_name
            )

            if os.path.exists(out_path):
                data = load_json(out_path)
            else:
                data = {}

            session_id = os.path.splitext(os.path.basename(src_path))[0][:27]

            data[session_id] = metrics

            save_json(out_path, data)

            print(f"Saved model metrics: {out_path}")


def count_users_metrics():
    os.makedirs(METRICS_FOLDER, exist_ok=True)

    all_users = {}

    for filename in os.listdir(USERS_FOLDER):

        if not filename.endswith(".json"):
            continue

        user_id = filename.replace("_full.json", "")

        src_path = os.path.join(USERS_FOLDER, filename)
        user_data = load_json(src_path)

        metrics = compute_metrics(user_data)

        all_users[user_id] = metrics

    out_path = os.path.join(METRICS_FOLDER, "users.json")

    save_json(out_path, all_users)

    print(f"Saved users metrics: {out_path}")


def aggregate_metrics(file_path):
    data = load_json(file_path)

    history_list = data.values()

    agg = defaultdict(list)

    for metrics in history_list:
        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                agg[k].append(v)

    return {
        k: mean(v)
        for k, v in agg.items()
    }


def aggregate_metrics_dicts_list(list_of_metrics):
    agg = defaultdict(list)

    for metrics in list_of_metrics:
        if not isinstance(metrics, dict):
            continue

        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                agg[k].append(v)

    return {
        k: mean(v) if v else 0.0
        for k, v in agg.items()
    }

def aggregate_metrics_folder():
    results = {}

    for filename in os.listdir(METRICS_FOLDER):

        if not filename.endswith(".json"):
            continue

        file_path = os.path.join(METRICS_FOLDER, filename)

        id = filename.replace(".json", "")

        data = load_json(file_path)

        if isinstance(data, list):
            agg = aggregate_metrics_dicts_list(data)

        elif isinstance(data, dict):

            if all(isinstance(v, dict) for v in data.values()):
                agg = aggregate_metrics_dicts_list(list(data.values()))
            else:
                agg = aggregate_metrics(data)

        else:
            continue

        results[id] = agg

        results[id]["launches_count"] = len(data)

    save_json(RESULTS_FILE_PATH, results)

    return results


def build_results_table():
    data = load_json(RESULTS_FILE_PATH)

    rows = []

    for file_name, metrics in data.items():

        row = {"file": file_name}

        for k, v in metrics.items():
            row[k] = v

        rows.append(row)

    df = pd.DataFrame(rows)

    return df

def print_results_table():
    df = build_results_table()

    df = df.sort_values(by="file")

    with pd.option_context(
        "display.max_columns", None,
        "display.width", 200
    ):
        print("\n=== METRICS SUMMARY ===\n")
        print(df.to_string(index=False))

def save_results_to_xlsx():
    df = build_results_table()

    df = df.sort_values(by="file")

    df.to_excel(TABLE_FILE_PATH, index=False, engine="openpyxl")

    print(f"Saved XLSX table: {TABLE_FILE_PATH}")


count_models_metrics()
count_users_metrics()

aggregate_metrics_folder()

save_results_to_xlsx()