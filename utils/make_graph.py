import json
import collections
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def load_quest(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    raise ValueError("Не удалось найти список узлов в JSON.")

def build_graph(nodes: list):
    by_id = {n["id"]: n for n in nodes}

    G = nx.MultiDiGraph()
    node_meta = {}

    for n in nodes:
        t = n.get("type", "")
        if t in ("scene", "end", "start"):
            is_cp = ("checkpoint_num" in n)
            short_label = n.get("number") or n["id"]
            node_meta[n["id"]] = {
                "type": t,
                "is_checkpoint": is_cp,
                "label": short_label,
            }
            G.add_node(n["id"])

    for n in nodes:
        t = n.get("type", "")
        nid = n["id"]

        if t == "scene":
            target_id = n.get("target")
            if target_id:
                target_node = by_id.get(target_id)
                if target_node and target_node.get("type") == "choice":
                    for branch in target_node.get("branches", []):
                        dest = branch.get("target")
                        if dest and dest in G.nodes:
                            label = branch.get("branch_text", "")
                            G.add_edge(nid, dest, branch_text=label)
                elif target_id in G.nodes:
                    G.add_edge(nid, target_id, branch_text="")

        elif t == "choice":
            pass

    return G, node_meta

COLOR_CHECKPOINT = "#E76F51"   # начало / чекпойнты
COLOR_SCENE      = "#4D96FF"   # обычные сцены
COLOR_END        = "#2A9D8F"   # концовки

def node_color(meta: dict) -> str:
    if meta["type"] == "end":
        return COLOR_END
    if meta["is_checkpoint"]:
        return COLOR_CHECKPOINT
    return COLOR_SCENE


def compute_layout(G: nx.MultiDiGraph, node_meta: dict) -> dict:
    start = None
    for nid, m in node_meta.items():
        if m["is_checkpoint"] and m["type"] == "scene":
            start = nid
            break
    if start is None:
        for nid, m in node_meta.items():
            if m["type"] == "scene":
                start = nid
                break
    if start is None:
        start = list(G.nodes)[0]

    try:
        layers = {}
        queue = collections.deque([(start, 0)])
        visited = {start}
        while queue:
            nid, lvl = queue.popleft()
            layers[nid] = lvl
            for _, succ in G.out_edges(nid):
                if succ not in visited:
                    visited.add(succ)
                    queue.append((succ, lvl + 1))
        max_lvl = max(layers.values(), default=0)
        for nid in G.nodes:
            if nid not in layers:
                max_lvl += 1
                layers[nid] = max_lvl

        level_nodes = collections.defaultdict(list)
        for nid, lvl in layers.items():
            level_nodes[lvl].append(nid)

        pos = {}
        for lvl, nids in level_nodes.items():
            count = len(nids)
            for i, nid in enumerate(nids):
                x = (i - (count - 1) / 2) * 1.0
                y = -lvl * 1.0
                pos[nid] = (x, y)
        return pos

    except Exception:
        try:
            return nx.kamada_kawai_layout(G)
        except Exception:
            return nx.spring_layout(G, seed=42)

def draw_quest_graph(nodes: list, output_path: str = "quest_graph.png"):
    G, node_meta = build_graph(nodes)

    if len(G.nodes) == 0:
        print("Не найдено ни одной сцены или концовки.")
        return

    pos = compute_layout(G, node_meta)

    node_ids   = list(G.nodes)
    colors     = [node_color(node_meta[n]) for n in node_ids]
    labels     = {n: node_meta[n]["label"] for n in node_ids}

    n = len(node_ids)
    fig_w = max(10, int(n * 0.5))
    fig_h = max(8, int(n * 0.35))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=120)
    ax.set_axis_off()
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    node_size = max(400, min(1200, 12000 // max(n, 1)))

    nx.draw_networkx_nodes(
        G, pos,
        nodelist=node_ids,
        node_color=colors,
        node_size=node_size,
        ax=ax,
        linewidths=1.2,
        edgecolors="#FFFFFF44",
    )

    nx.draw_networkx_labels(
        G, pos,
        labels=labels,
        font_size=max(6, min(10, 180 // max(n, 1))),
        font_color="#FFFFFF",
        font_weight="bold",
        ax=ax,
    )

    edge_list = list(G.edges(keys=True))

    pair_count = collections.defaultdict(int)
    for u, v, k in edge_list:
        pair_count[(u, v)] += 1

    pair_seen = collections.defaultdict(int)
    edge_styles_map = {}

    for u, v, k in edge_list:
        total = pair_count[(u, v)]
        idx   = pair_seen[(u, v)]
        pair_seen[(u, v)] += 1

        if total == 1:
            rad = 0.08
        else:
            max_rad = 0.35
            if total > 1:
                rad = -max_rad + (2 * max_rad / (total - 1)) * idx if total > 1 else 0.0
            else:
                rad = 0.0

        edge_styles_map[(u, v, k)] = f"arc3,rad={rad:.3f}"

    for u, v, k in edge_list:
        rad = float(edge_styles_map[(u, v, k)].split("rad=")[-1])

        nx.draw_networkx_edges(
            G, pos,
            edgelist=[(u, v, k)],
            ax=ax,
            arrowstyle="-|>",
            arrowsize=16,
            edge_color="black",
            width=1.2,
            node_size=node_size,
            connectionstyle=f"arc3,rad={rad}",
            alpha=0.85,
            min_source_margin=2,
            min_target_margin=2,
        )

    legend_handles = [
        mpatches.Patch(color=COLOR_CHECKPOINT, label="Начало, чекпойнт"),
        mpatches.Patch(color=COLOR_SCENE,      label="Обычная сцена"),
        mpatches.Patch(color=COLOR_END,        label="Концовка"),
    ]

    ax.legend(
        handles=legend_handles,
        loc="lower left",
        framealpha=0.9,
        facecolor="white",
        edgecolor="black",
        fontsize=100,
    )

    plt.title("Граф квеста", color="white", fontsize=14, pad=12)
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", dpi=120)
    plt.close(fig)


if __name__ == "__main__":

    json_path   = "models_framework/quests/quest.json"
    out_path = "pic/iq2.png"

    quest_nodes = load_quest(json_path)
    draw_quest_graph(quest_nodes, out_path)