import csv
import os
from core.matcher import match

EVAL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "eval_set.csv"
)


def load_eval():
    if not os.path.exists(EVAL_PATH):
        return []
    rows = []
    with open(EVAL_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def run_eval(min_score=0.2):
    rows = load_eval()
    if not rows:
        return {"error": "评测集为空或找不到 data/eval_set.csv"}

    tp = fp = fn = tn = 0
    top3_hit = 0
    total_pairs = 0

    for row in rows:
        if row["type"] != "正确对":
            continue
        total_pairs += 1
        target = {
            "type": "寻物",
            "title": row["lost_desc"],
            "description": row["lost_desc"],
            "category": row["category"],
            "location": row["location"],
            "time": f"{row['time']} 12:00",
            "color": "" if row["color"] == "无" else row["color"],
            "brand": "" if row["brand"] == "无" else row["brand"],
        }
        candidate = {
            "type": "招领",
            "item_id": 1,
            "title": row["found_desc"],
            "description": row["found_desc"],
            "category": row["category"],
            "location": row["location"],
            "time": f"{row['time']} 12:00",
            "color": "" if row["color"] == "无" else row["color"],
            "brand": "" if row["brand"] == "无" else row["brand"],
        }
        results = match(target, [candidate], min_score=min_score)
        if results and results[0]["score"] >= min_score:
            tp += 1
            top3_hit += 1
        else:
            fn += 1

    recall = tp / total_pairs if total_pairs else 0
    return {
        "总正确对数": total_pairs,
        "命中数": tp,
        "漏召数": fn,
        "召回率": round(recall, 3),
        "Top-3命中率": round(top3_hit / total_pairs, 3) if total_pairs else 0,
    }