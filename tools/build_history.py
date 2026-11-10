#!/usr/bin/env python3
"""Build docs/data/history.json: what happened to past ICLR papers by starting rank.

Reads the local previous/ folder (never committed) and writes counts only.
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

ACCEPTED = {"Poster", "Spotlight", "Oral"}
SKIPPED = {"Desk Reject", None}
BAND_WIDTH = 2
YEARS = [2024, 2025]


def parse(paper):
    """Return (before, after) rating lists, or None if any review cannot be read."""
    before, after = [], []
    for review in paper["review"].values():
        parts = str(review["rating"]).split(";")
        try:
            before.append(float(parts[0]))
            after.append(float(parts[1]))
        except (ValueError, IndexError):
            return None
    return (before, after) if before else None


def build(insights, statuses, seed=7):
    rng = random.Random(seed)
    papers = []
    for paper in insights:
        status, ratings = statuses.get(paper["id"]), parse(paper)
        if status not in SKIPPED and ratings:
            papers.append((status, *ratings))
    means = [sum(before) / len(before) for _, before, _ in papers]
    count, above, seen = Counter(means), {}, 0
    for value in sorted(count, reverse=True):
        above[value] = seen
        seen += count[value]
    # [n, withdrawn, stayed_same, accepted_same, stayed_changed, accepted_changed]
    bands = [[0] * 6 for _ in range(100 // BAND_WIDTH)]
    paired = raised = lowered = 0
    for (status, before, after), value in zip(papers, means):
        # Tied papers are spread at random over the ranks they share.
        top_percent = 100 * (above[value] + rng.random() * count[value]) / len(papers)
        band = bands[min(int(top_percent // BAND_WIDTH), len(bands) - 1)]
        band[0] += 1
        for old, new in zip(sorted(before), sorted(after)):
            paired += 1
            raised += new > old
            lowered += new < old
        if status == "Withdraw":
            band[1] += 1
        else:
            offset = 2 if before == after else 4
            band[offset] += 1
            band[offset + 1] += status in ACCEPTED
    return {
        "papers": len(papers), "withdrawn": sum(band[1] for band in bands),
        "reviews_paired": paired, "reviews_raised": raised, "reviews_lowered": lowered,
        "bands": bands,
    }


def main(argv):
    source, target = Path(argv[1]), Path(argv[2])
    years = {}
    for year in YEARS:
        insights = json.loads(next(source.glob(f"iclr{year}_threshold6_*_reviewers.json")).read_text())
        statuses = {p["id"]: p.get("status") for p in json.loads((source / f"iclr{year}.json").read_text())}
        years[str(year)] = build(insights, statuses)
    target.write_text(json.dumps({"band_width": BAND_WIDTH, "years": years}, separators=(",", ":")))
    for year, data in years.items():
        print(year, {k: v for k, v in data.items() if k != "bands"})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
