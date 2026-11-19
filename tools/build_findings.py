#!/usr/bin/env python3
"""Build docs/data/findings.json: totals only, no paper is listed.

Usage: build_findings.py RAW_SNAPSHOT_DIR STATE_DIR PREVIOUS_DIR OUT_JSON
RAW_SNAPSHOT_DIR is one folder written by download.py (the final one).
STATE_DIR holds the per-snapshot summaries written by build_site.py.
PREVIOUS_DIR holds the past-year files that build_history.py reads.
"""
import gzip
import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_history

DEADLINE = datetime(2026, 11, 19, 12, tzinfo=timezone.utc)  # Nov 18, anywhere on Earth
RELEASED = datetime(2026, 11, 7, tzinfo=timezone.utc)  # reviews came out on Nov 6
REMINDER = datetime(2026, 11, 17, 6, tzinfo=timezone.utc)
SCORES = [2.0, 2.25, 2.3333, 2.5, 2.6667, 2.75, 3.0, 3.3333]


def ms(d):
    return d.timestamp() * 1000


def mean(a):
    return sum(a) / len(a)


def pct(a, b):
    return round(100 * a / b, 1) if b else 0.0


def value(content, key):
    return (content.get(key) or {}).get("value")


def load_papers(raw):
    papers = []
    for page in sorted(Path(raw).glob("page_*.json.gz")):
        for note in json.load(gzip.open(page)):
            reviews = []
            for reply in note.get("details", {}).get("directReplies", []):
                if not any(i.endswith("/-/Official_Review") for i in reply.get("invitations", [])):
                    continue
                c = reply["content"]
                rating, conf = value(c, "rating"), value(c, "confidence")
                if rating is None:
                    continue
                num = lambda v: int(str(v).split(":")[0]) if v is not None else None
                reviews.append({"r": num(rating), "c": num(conf), "cd": reply["cdate"], "md": reply["mdate"],
                                "s": num(value(c, "soundness")), "p": num(value(c, "presentation")), "i": num(value(c, "informativeness"))})
            papers.append({"n": str(note["number"]), "status": value(note["content"], "venueid").split("/")[-1],
                           "area": value(note["content"], "primary_area"), "revs": reviews})
    return papers


def top_range(dist, score):
    n = sum(c for _, c in dist)
    above = sum(c for m, c in dist if m > score + 1e-3)
    tied = sum(c for m, c in dist if abs(m - score) <= 1e-3)
    return [pct(above, n), pct(above + tied, n)]


def direction(a, b):
    if not a or not b or len(a) != len(b):
        return None
    d = sum(b) - sum(a)
    return "up" if d > 0 else "down" if d < 0 else "same"


def past_years(previous, width=4, seed=7):
    """Accepted share by rank after the rebuttal, for papers still in at the decision."""
    rng, out = random.Random(seed), {}
    for year in build_history.YEARS:
        insights = json.loads(next(Path(previous).glob(f"iclr{year}_threshold6_*_reviewers.json")).read_text())
        statuses = {p["id"]: p.get("status") for p in json.loads((Path(previous) / f"iclr{year}.json").read_text())}
        rows = []
        for paper in insights:
            status, ratings = statuses.get(paper["id"]), build_history.parse(paper)
            if ratings and status not in build_history.SKIPPED and status != "Withdraw":
                rows.append((mean(ratings[1]), status in build_history.ACCEPTED))
        count, above, seen = Counter(m for m, _ in rows), {}, 0
        for value in sorted(count, reverse=True):
            above[value] = seen
            seen += count[value]
        bands = [[0, 0] for _ in range(100 // width)]
        for m, ok in rows:
            # Tied papers are spread at random over the ranks they share.
            band = bands[min(int(100 * (above[m] + rng.random() * count[m]) / len(rows) // width), len(bands) - 1)]
            band[0] += 1
            band[1] += ok
        out[str(year)] = {"papers": len(rows), "accepted": sum(ok for _, ok in rows), "bands": bands}
    return {"band_width": width, "years": out}


def build(raw, state, previous):
    papers = load_papers(raw)
    snaps = [json.loads(p.read_text()) for p in sorted(Path(state).glob("*.json"))]
    first, last = snaps[0]["ratings_by_paper"], snaps[-1]["ratings_by_paper"]
    active = [p for p in papers if p["status"] == "Submission" and p["revs"]]
    withdrawn = {p["n"] for p in papers if p["status"] == "Withdrawn_Submission"}
    edited = lambda r: r["md"] > ms(RELEASED)

    moved = Counter(direction(first.get(p["n"]), last.get(p["n"])) for p in active)

    odds = defaultdict(Counter)
    for n, a in first.items():
        if not a:
            continue
        row = odds[round(mean(a), 2)]
        row["n"] += 1
        row["withdrew" if n in withdrawn else direction(a, last.get(n)) or "other"] += 1
        if n not in withdrawn and last.get(n):
            row["stayed"] += 1
            row["high"] += mean(last[n]) >= 2.666
    odds = [{"score": s, "n": r["n"], "withdrew": r["withdrew"], "up": r["up"], "down": r["down"], "stayed": r["stayed"], "high": r["high"]}
            for s, r in sorted(odds.items()) if r["n"] >= 200]

    high = [n for n, b in last.items() if b and mean(b) >= 2.666 and first.get(n)]
    origin = Counter("2.67 or higher" if mean(first[n]) >= 2.666 else "2.33 to 2.5" if mean(first[n]) >= 2.3 else "2.0 to 2.25" if mean(first[n]) >= 1.99 else "below 2.0" for n in high)
    low = [p for p in active if first.get(p["n"]) and mean(first[p["n"]]) <= 1.7]
    low_all = sum(1 for a in first.values() if a and mean(a) <= 1.7)

    timeline = []
    for s in snaps:
        c = Counter(direction(first.get(n), b) for n, b in s["ratings_by_paper"].items())
        timeline.append({"t": s["taken_at"], "up": c["up"], "down": c["down"], "withdrawn": s["withdrawn"],
                         "ranks": [top_range(s["mean_distribution"], x) for x in SCORES]})

    def share_at_least(dist, x):
        return pct(sum(c for m, c in dist if m >= x - 1e-3), sum(c for _, c in dist))

    # Day-one rating of each review: an unedited review kept its rating; the rest are matched in sorted order.
    peers, by_conf, moves = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    for p in active:
        f = first.get(p["n"])
        if not f or len(f) != len(p["revs"]):
            continue
        left = Counter(f) - Counter(r["r"] for r in p["revs"] if not edited(r))
        changed = sorted((r for r in p["revs"] if edited(r)), key=lambda r: r["r"])
        if sum(left.values()) != len(changed):
            continue
        start = [(r, r["r"]) for r in p["revs"] if not edited(r)] + list(zip(changed, sorted(left.elements())))
        for r, was in start:
            moves[was]["n"] += 1
            moves[was]["up"] += r["r"] > was
            moves[was]["down"] += r["r"] < was
            by_conf[was, r["c"]]["n"] += 1
            by_conf[was, r["c"]]["up"] += r["r"] > was
            if len(start) == 3:
                others = sorted(w for q, w in start if q is not r)
                peers[was, tuple(others)]["n"] += 1
                peers[was, tuple(others)]["up"] += r["r"] > was
    peers = [{"own": own, "others": list(o), "n": c["n"], "up": pct(c["up"], c["n"])} for (own, o), c in sorted(peers.items()) if c["n"] >= 400 and own < 4]
    review_moves = [{"from": x, "n": moves[x]["n"], "up": moves[x]["up"], "down": moves[x]["down"]} for x in range(1, 5)]
    conf_moves = [{"own": own, "level": c, "n": v["n"], "up": pct(v["up"], v["n"])} for (own, c), v in sorted(by_conf.items(), key=lambda x: (x[0][0], x[0][1] or 0)) if c and own < 3]

    scored = [r for p in papers for r in p["revs"] if r["s"] and r["p"] and r["i"]]

    def grid(row, col):
        cells = defaultdict(Counter)
        for r in scored:
            cells[r[row], r[col]]["n"] += 1
            cells[r[row], r[col]]["ok"] += r["r"] >= 3
        return [[{"n": cells[a, b]["n"], "accept": pct(cells[a, b]["ok"], cells[a, b]["n"])} for b in (1, 2, 3)] for a in (1, 2, 3)]
    top = {k: {"share": pct(sum(r[k] == 3 for r in scored), len(scored)),
               "accept": pct(sum(r[k] == 3 and r["r"] >= 3 for r in scored), sum(r[k] == 3 for r in scored))} for k in "spi"}
    all_top = [r["r"] for r in scored if r["s"] == r["p"] == r["i"] == 3]
    subs = {"n": len(scored), "top": top, "by_informativeness": grid("s", "i"), "by_presentation": grid("s", "p"),
            "all_top": {"n": len(all_top), "reject": pct(sum(x <= 2 for x in all_top), len(all_top))}}

    # Luck: how much of a rating is the paper, and how close papers sit to the 2.67 line.
    groups = [[r["r"] for r in p["revs"]] for p in active if len(p["revs"]) >= 2]
    total_n = sum(len(g) for g in groups)
    grand = sum(sum(g) for g in groups) / total_n
    between = sum(len(g) * (mean(g) - grand) ** 2 for g in groups) / (len(groups) - 1)
    within = sum(sum((x - mean(g)) ** 2 for x in g) for g in groups) / (total_n - len(groups))
    k0 = (total_n - sum(len(g) ** 2 for g in groups) / total_n) / (len(groups) - 1)
    pairs = same = 0
    for g in groups:
        ok = sum(x >= 3 for x in g)
        pairs += len(g) * (len(g) - 1) // 2
        same += ok * (ok - 1) // 2 + (len(g) - ok) * (len(g) - ok - 1) // 2
    share_ok = sum(x >= 3 for g in groups for x in g) / total_n
    three = Counter(sum(g) for g in groups if len(g) == 3)
    luck = {"from_paper": pct(between - within, between + (k0 - 1) * within), "same_side": pct(same, pairs),
            "same_side_chance": round(100 * (share_ok ** 2 + (1 - share_ok) ** 2), 1), "papers": sum(three.values()),
            "sums": [{"sum": k, "n": three[k]} for k in range(3, 13)]}

    by_count = defaultdict(Counter)
    flipped = Counter()
    for p in active:
        g = [r["r"] for r in sorted(p["revs"], key=lambda r: r["cd"])]
        if 3 <= len(g) <= 5:
            c = by_count[len(g)]
            c["n"] += 1
            c["high"] += mean(g) >= 2.666
            c["points"] += sum(g)
            c["reviews"] += len(g)
        if len(g) == 4 and mean(g[:3]) >= 2.666:
            flipped["n"] += 1
            flipped["fell"] += mean(g) < 2.666
    fourth = {"by_count": [{"reviewers": k, "n": c["n"], "high": pct(c["high"], c["n"]), "mean": round(c["points"] / c["reviews"], 2)} for k, c in sorted(by_count.items())],
              "first_three_high": flipped["n"], "fell": flipped["fell"]}

    areas = defaultdict(lambda: Counter())
    for p in papers:
        a = areas[p["area"]]
        a["n"] += 1
        a["withdrew"] += p["status"] == "Withdrawn_Submission"
        f, l = first.get(p["n"]), last.get(p["n"])
        if p["status"] == "Submission" and l and f:
            a["first_n"] += 1
            a["first_high"] += mean(f) >= 2.666
        if p["status"] == "Submission" and l:
            a["last_n"] += 1
            a["last_high"] += mean(l) >= 2.666
            d = direction(f, l)
            a["paired"] += d is not None
            a["up"] += d == "up"
    areas = sorted(({"name": k, "n": a["n"], "withdrew": pct(a["withdrew"], a["n"]), "first_high": pct(a["first_high"], a["first_n"]),
                     "last_high": pct(a["last_high"], a["last_n"]), "up": pct(a["up"], a["paired"])}
                    for k, a in areas.items() if a["n"] >= 300), key=lambda a: -a["last_high"])

    def spread(ratings):
        c = Counter(max(a) - min(a) for a in ratings)
        return [pct(c[k], sum(c.values())) for k in range(4)]
    stayed = [n for n in last if first.get(n) and last[n]]
    gap = Counter()
    for n in stayed:
        if len(first[n]) == len(last[n]):
            was, now = max(first[n]) - min(first[n]), max(last[n]) - min(last[n])
            gap["closer" if now < was else "wider" if now > was else "same"] += 1

    day_one_all = mean([mean(a) for a in first.values() if a])
    day_one_stayed = mean([mean(first[n]) for n in stayed])
    final = mean([mean(last[n]) for n in last if last[n]])
    edit_times = [r["md"] for p in papers for r in p["revs"]]
    before = sum(ms(REMINDER) - 3 * 3600e3 <= t < ms(REMINDER) for t in edit_times)
    after = sum(ms(REMINDER) <= t < ms(REMINDER) + 3 * 3600e3 for t in edit_times)

    return {
        "first": snaps[0]["taken_at"], "last": snaps[-1]["taken_at"], "deadline": DEADLINE.isoformat(),
        "totals": {"papers": len(papers), "active": len(active), "withdrawn": len(withdrawn), "reviews": len(edit_times),
                   "up": moved["up"], "down": moved["down"], "same": moved["same"]},
        "past": past_years(previous),
        "reshuffle": {"n": len(high), "from": [{"band": b, "n": origin[b]} for b in ("2.67 or higher", "2.33 to 2.5", "2.0 to 2.25", "below 2.0")]},
        "odds": odds,
        "low": {"started": low_all, "stayed": len(low), "reached_2_5": sum(mean(last[p["n"]]) >= 2.5 for p in low)},
        "scores": SCORES, "timeline": timeline,
        "share": {"2.67": [share_at_least(snaps[0]["mean_distribution"], 2.6667), share_at_least(snaps[-1]["mean_distribution"], 2.6667)],
                  "3.0": [share_at_least(snaps[0]["mean_distribution"], 3.0), share_at_least(snaps[-1]["mean_distribution"], 3.0)]},
        "mean": {"day_one": round(day_one_all, 3), "day_one_stayed": round(day_one_stayed, 3), "final": round(final, 3)},
        "luck": luck, "fourth": fourth, "subs": subs, "review_moves": review_moves, "peers": peers, "conf_moves": conf_moves, "areas": areas,
        "edits": {"reminder": REMINDER.isoformat(), "three_hours_before": before, "three_hours_after": after},
        "spread": {"day_one": spread([first[n] for n in stayed]), "final": spread([last[n] for n in stayed]), "closer": gap["closer"], "wider": gap["wider"]},
    }


def only_numbers(doc):
    """Fail if any long free text other than area names got in."""
    def walk(x, key=""):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, k)
        elif isinstance(x, list):
            for v in x:
                walk(v, key)
        elif isinstance(x, str) and key not in ("name", "band"):
            assert re.fullmatch(r"[0-9T:+.Z-]+", x), x
    walk(doc)


if __name__ == "__main__":
    out = build(sys.argv[1], sys.argv[2], sys.argv[3])
    only_numbers(out)
    Path(sys.argv[4]).write_text(json.dumps(out, separators=(",", ":")))
    print("wrote", sys.argv[4], Path(sys.argv[4]).stat().st_size, "bytes")
