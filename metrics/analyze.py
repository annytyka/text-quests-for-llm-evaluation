import json
import os
from collections import defaultdict


def load_output(path):
    if not os.path.exists(path):
        return {}

    if os.path.isdir(path):
        raise ValueError(f"{path} is a directory, not a file")

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def process_all(old_dir, output_path):
    out = load_output(output_path)

    for subdir in os.listdir(old_dir):
        old_subdir = os.path.join(old_dir, subdir)

        if not os.path.isdir(old_subdir):
            continue

        for file in os.listdir(old_subdir):
            file_path = os.path.join(old_subdir, file)

            if not os.path.isfile(file_path):
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            model = data.get("model", "unknown")
            mode = data.get("mode", "unknown")
            lang = data.get("lang", "unknown")
            type = data.get("summarize_type", "unknown")
            started_at = data.get("started_at", "unknown")

            endings = data.get("endings_opened", {})

            key = f"{model}|{mode}|{lang}|{type}|{started_at}"

            unopened = sorted(
                int(k) for k, v in endings.items()
                if int(v) == 0
            )

            out[key] = unopened

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


old_dir = "data_models" 
new_file = "metrics/analitycs.json"

# process_all(old_dir, new_file)



def aggregate_unfound_endings(old_dir, output_path):
    stats = defaultdict(lambda: defaultdict(int))

    for subdir in os.listdir(old_dir):
        old_subdir = os.path.join(old_dir, subdir)

        if not os.path.isdir(old_subdir):
            continue

        for file in os.listdir(old_subdir):
            file_path = os.path.join(old_subdir, file)

            if not os.path.isfile(file_path):
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            model = data.get("model", "unknown")
            mode = data.get("mode", "unknown")
            lang = data.get("lang", "unknown")
            summarize_type = data.get("summarize_type", "unknown")

            key = (model, mode, lang, summarize_type)

            endings = data.get("endings_opened", {})

            for ending_id, value in endings.items():
                if int(value) == 0:
                    stats[key][int(ending_id)] += 1

    result = {}

    for (model, mode, lang, summarize_type), ending_counts in stats.items():

        sorted_endings = sorted(
            ending_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        composite_key = f"{model}|{mode}|{lang}|{summarize_type}"

        result[composite_key] = {
            str(k): v for k, v in sorted_endings
        }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


old_dir = "data_models"
new_file = "metrics/model_unfound_endings_2.json"

aggregate_unfound_endings(old_dir, new_file)