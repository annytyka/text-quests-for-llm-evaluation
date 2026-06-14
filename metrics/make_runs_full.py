import json
import os

FOLDER = "models_framework"
QUEST_PATH = FOLDER + "/quests/quest_translated.json"
FIRST_SCENE_ID = "scene_1"

with open(QUEST_PATH, "r", encoding="utf-8") as f:
    QUEST_DATA = json.load(f)

def extract_checkpoints(quest_data):
    checkpoints = []

    for node in quest_data:
        if node.get("type") == "scene":
            if node.get("checkpoint_num") is not None:
                checkpoints.append({
                    "scene_id": node["id"],
                    "checkpoint_num": node["checkpoint_num"]
                })

    checkpoints.sort(key=lambda x: x["checkpoint_num"])

    return checkpoints

checkpoints = extract_checkpoints(QUEST_DATA)

scene_to_cp = {
    cp["scene_id"]: cp["checkpoint_num"]
    for cp in checkpoints
}

def get_cp_num(scene_id):
    return scene_to_cp.get(scene_id)


def go_run(distances, run_scenes, run_choices):
    if not run_scenes:
        return distances
    
    first_cp = get_cp_num(run_scenes[0])
    if first_cp >= len(checkpoints) - 1:
        return distances
    
    new_distances = [[] for _ in distances] # для 0 1 2 3 4
    
    way_choices = []
    if all(
        (cp := get_cp_num(scene)) is None or cp == first_cp
        for scene in run_scenes
    ):
        return distances
    
    current_cp = first_cp
    new_distances[current_cp].append(run_scenes[0])

    last_cp_index = None

    for i, scene in enumerate(run_scenes):
        if get_cp_num(scene) is not None:
            last_cp_index = i

    for i in range(last_cp_index + 1):
        if run_choices[i] == "0":
            new_cp = get_cp_num(run_scenes[i]) 
            new_distances[current_cp].pop()
            way_choices.pop()
            if new_cp is not None:
                current_cp -= 1
        else:
            new_scene = run_scenes[i + 1]
            new_cp = get_cp_num(new_scene)
            if new_cp is not None:
                if (distances[current_cp] is None 
                    or (new_distances[current_cp] is not None 
                        and len(new_distances[current_cp]) > 1
                        and len(new_distances[current_cp]) < len(distances[current_cp])
                        )
                    ):
                    distances[current_cp] = new_distances[current_cp].copy()
                current_cp += 1
            new_distances[current_cp].append(new_scene)
            way_choices.append(run_choices[i])

    return distances
            

def go_user(user_file_path, new_dir):
    with open(user_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    runs = data.get("runs", [])

    num_runs = len(runs)

    num_runs = len(runs)

    distances = [None for _ in range(len(checkpoints))]

    for i in range(num_runs):
        run = runs[i]
        full_run = run.copy()

        run_scenes = run.get("scenes_history", [])
        first_cp = get_cp_num(run_scenes[0])
        if first_cp != FIRST_SCENE_ID: 
            run_choices = run.get("choices_history", [])
            distances = go_run(distances, run_scenes, run_choices)
            full_run = []
            for j in range(first_cp):
                full_run += distances[j]
            full_run += run_scenes

        run["full_run"] = full_run

    data["runs"] = runs

    os.makedirs(new_dir, exist_ok=True)

    _, ext = os.path.splitext(user_file_path)
    filename = os.path.splitext(os.path.basename(user_file_path))[0]
    new_path = os.path.join(new_dir, filename + "_full" + ext)

    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"User {filename} done")


# old_dir = "data_models"
# new_dir = "data_models_full"

# os.makedirs(new_dir, exist_ok=True)

# for subdir in os.listdir(old_dir):
#     old_subdir = os.path.join(old_dir, subdir)
#     if not os.path.isdir(old_subdir):
#         continue
#     new_subdir = os.path.join(new_dir, subdir)
#     os.makedirs(new_subdir, exist_ok=True)
#     for file in os.listdir(old_subdir):
#         file_path = os.path.join(old_subdir, file)

#         if os.path.isfile(file_path):
#             go_user(file_path, new_subdir)



# old_dir = "data_users"
# new_dir = "data_users_full"

# os.makedirs(new_dir, exist_ok=True)

# for file in os.listdir(old_dir):
#     file_path = os.path.join(old_dir, file)

#     if os.path.isfile(file_path):
#         go_user(file_path, new_dir)












# from collections import defaultdict, deque

# def build_empirical_graph(runs):
#     graph = defaultdict(set)

#     for run in runs:
#         scenes = run["scenes_history"]

#         for i in range(len(scenes) - 1):
#             a, b = scenes[i], scenes[i + 1]

#             if a != b:
#                 graph[a].add(b)

#     return graph

# def bfs(graph, start, target):
#     queue = deque([start])
#     prev = {start: None}

#     while queue:
#         node = queue.popleft()

#         if node == target:
#             break

#         for nxt in graph.get(node, []):
#             if nxt not in prev:
#                 prev[nxt] = node
#                 queue.append(nxt)

#     if target not in prev:
#         return None

#     path = []
#     cur = target

#     while cur is not None:
#         path.append(cur)
#         cur = prev[cur]

#     return path[::-1]