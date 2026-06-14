import json

INPUT = "YOUR_PATH_TO_QUEST_INI"
OUTPUT = "YOUR_PATH_TO_QUEST_JSON"

def parse_quest_ini(path, output_path):

    with open(path, encoding="utf-8-sig") as f:
        lines = f.readlines()

    sections = {}
    current = None

    for raw in lines:
        line = raw.strip()

        if not line:
            continue

        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            sections[current] = {}
            continue

        if "=" in line and current:
            k, v = line.split("=", 1)
            sections[current][k.strip()] = v.strip()

    result = []

    end_nodes = {}
    end_texts = {}

    for sec_id, data in sections.items():
        if "end" in data:
            end_id = data["end"]
            text = data.get("0", "")

            end_nodes[sec_id] = end_id

            if end_id not in end_texts:
                end_texts[end_id] = text

    for end_id, text in end_texts.items():
        result.append({
            "id": f"end_{end_id}",
            "type": "end",
            "number": end_id,
            "text": text
        })

    for sec_id, data in sections.items():

        if sec_id == "endings":
            continue

        if sec_id in end_nodes:
            continue

        if "win" in data and "fail" in data:

            scene_id = f"scene_{sec_id}"
            choice_id = f"choice_{sec_id}"

            win_target_raw = data["win"]
            fail_target_raw = data["fail"]

            if win_target_raw in end_nodes:
                win_target = f"end_{end_nodes[win_target_raw]}"
            else:
                win_target = f"scene_{win_target_raw}"

            if fail_target_raw in end_nodes:
                fail_target = f"end_{end_nodes[fail_target_raw]}"
            else:
                fail_target = f"scene_{fail_target_raw}"

            result.append({
                "id": scene_id,
                "type": "scene",
                "text": "Тебе предстоит испытание.",
                "target": choice_id
            })

            result.append({
                "id": choice_id,
                "type": "choice",
                "branches": [
                    {
                        "branch_id": "1",
                        "branch_text": "Справиться",
                        "target": win_target
                    },
                    {
                        "branch_id": "2",
                        "branch_text": "Не справиться",
                        "target": fail_target
                    }
                ]
            })

            continue

        scene_id = f"scene_{sec_id}"

        scene_node = {
            "id": scene_id,
            "type": "scene",
            "text": data.get("0", "")
        }

        branches = []
        i = 1

        while True:
            k1 = str(i)
            k2 = str(i + 1)

            if k1 not in data or k2 not in data:
                break

            target = data[k1]
            text = data[k2]

            if target in end_nodes:
                tgt = f"end_{end_nodes[target]}"
            else:
                tgt = f"scene_{target}"

            branches.append({
                "branch_id": str(len(branches + 1)),
                "branch_text": text,
                "target": tgt
            })

            i += 2

        if branches:
            choice_id = f"choice_{sec_id}"
            scene_node["target"] = choice_id

            result.append(scene_node)

            result.append({
                "id": choice_id,
                "type": "choice",
                "branches": branches
            })
        else:
            result.append(scene_node)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    print("Готово. Концовок:", len(end_texts))

parse_quest_ini(INPUT, OUTPUT)
