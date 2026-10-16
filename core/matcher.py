import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

from core.synonyms import expand_text, same_category, same_location, STOP_WORDS

jieba.setLogLevel(20)


def parse_time(t):
    try:
        return datetime.strptime(t, "%Y-%m-%d %H:%M")
    except Exception:
        return None


def time_in_window(t1, t2, days=7):
    d1, d2 = parse_time(t1), parse_time(t2)
    if not d1 or not d2:
        return True
    return abs((d1 - d2).days) <= days


def color_conflict(target, c):
    c1 = (target.get("color") or "").strip()
    c2 = (c.get("color") or "").strip()
    if c1 and c2 and c1 != c2:
        return True
    return False


def brand_conflict(target, c):
    b1 = (target.get("brand") or "").strip()
    b2 = (c.get("brand") or "").strip()
    if b1 and b2 and b1 != b2:
        return True
    return False


def split_words(text):
    words = jieba.cut(expand_text(text or ""))
    return " ".join([w for w in words if w.strip() and w not in STOP_WORDS])


def build_text(item):
    parts = [
        item.get("title", ""),
        item.get("description", ""),
        item.get("color", "") or "",
        item.get("brand", "") or "",
    ]
    return " ".join([p for p in parts if p])


def hard_filter(target, candidates):
    results = []
    for c in candidates:
        if c["type"] == target["type"]:
            continue
        if not same_category(target.get("category", ""), c.get("category", "")):
            continue
        if not same_location(target.get("location", ""), c.get("location", "")):
            continue
        if not time_in_window(target.get("time", ""), c.get("time", "")):
            continue
        if color_conflict(target, c):
            continue
        if brand_conflict(target, c):
            continue
        results.append(c)
    return results


def explain(target, c):
    reasons = []
    if target.get("category") == c.get("category"):
        reasons.append("类别相同")
    elif same_category(target.get("category", ""), c.get("category", "")):
        reasons.append("类别相近")
    if target.get("location") == c.get("location"):
        reasons.append("地点相同")
    elif same_location(target.get("location", ""), c.get("location", "")):
        reasons.append("地点相近")
    if target.get("color") and target.get("color") == c.get("color"):
        reasons.append("颜色相同")
    if target.get("brand") and target.get("brand") == c.get("brand"):
        reasons.append("品牌相同")
    tw = set(jieba.cut(expand_text(target.get("description", ""))))
    cw = set(jieba.cut(expand_text(c.get("description", ""))))
    common = {w for w in (tw & cw) if len(w) > 1 and w.strip() and w not in STOP_WORDS}
    if common:
        reasons.append("描述关键词：" + "、".join(list(common)[:5]))
    return reasons


def score_candidates(target, candidates):
    if not candidates:
        return []
    docs = [split_words(build_text(target))] + [split_words(build_text(c)) for c in candidates]
    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform(docs)
    sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()

    results = []
    for i, c in enumerate(candidates):
        s = float(sims[i])
        level = "高" if s >= 0.75 else ("中" if s >= 0.6 else "低")
        results.append({
            "item": c,
            "score": round(s, 3),
            "level": level,
            "reasons": explain(target, c),
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:3]


def match(target, all_items, min_score=0.2):
    candidates = hard_filter(target, all_items)
    scored = score_candidates(target, candidates)
    return [r for r in scored if r["score"] >= min_score]