# ICLR 2027 Rebuttal Radar

See how ICLR 2027 review scores moved during the rebuttal, and where your paper stands. The rebuttal is over, but reviewers can still change scores during the closed discussion, so the site still updates every 12 hours.

Site: https://dipta007.github.io/iclr-2027-rebuttal-radar/

## Credit

This project is a fork of [iclr-2027-scores](https://github.com/shiqiangw/iclr-2027-scores) by shiqiangw. The original [ICLR 2027 Scores](https://shiqiangw.github.io/iclr-2027-scores/) page, the download and build pipeline, and the first snapshot (Nov 6) are their work. This fork adds the rebuttal-period sections and the 12-hour refresh.

## What the page shows

- **Where did my paper end up?** Type a paper number or title. You get the day-one and current scores, the rank as a range, and short answers for that paper: how papers at the same rank did in ICLR 2024 and 2025, what the score change was worth, and whether that was normal.
- **What moved.** How many papers went up, went down, got a different number of reviews, or left.
- **How much moved, compared with past years.** The share of raised review scores, next to past years.
- **Papers that moved.** A searchable list with scores before and after.
- **Score distribution, day one and now**, and the cut-offs for the top 5, 10, 25, and 50 percent.
- **Which scores moved**, and which score groups lost the most papers.
- **All papers**, ranked by mean score.

## What is published

Only paper numbers, titles, OpenReview forum ids, and numeric scores. The findings page adds totals and primary-area names. Review text, abstracts, authors, and reviewer ids are never copied, and `check_output()` in `build_site.py` stops the build if any other text reaches the page data. Withdrawn and desk-rejected papers are not listed.

Visits are counted with Cloudflare Web Analytics (no cookies). The looked-up paper number is kept in the `#` part of the address, which is not sent to any server.

Raw downloads hold review text. They stay in `snapshots/`, which git ignores. Per-paper summaries of each snapshot stay in `state/`, which git also ignores, so papers that later withdraw are not listed anywhere in the published data. Keep `state/`: the first-day summary in it is what every later update is compared with.

## How it is counted

- Only official reviews and their overall rating count.
- A paper "went up" if it has the same number of reviews as in the first snapshot and a higher mean. "Went down" is the same with a lower mean.
- Reviewer identities are not public, so scores are matched by sorted position inside each paper. Two opposite changes on one paper can hide each other.
- Scores go from 1 to 4, so many papers share a mean. A rank is therefore shown as a range.
- Past-year rates come from papers with a similar starting rank. They are not a prediction.

## Refresh every 12 hours

A launchd job runs the refresh at 7:10 and 19:10 local time. It also rebuilds the findings data.

```sh
./refresh.sh
```

It downloads a snapshot, rebuilds `docs/data/`, runs the tests, and pushes. It only reads from OpenReview. It commits only files under `docs/data/`, and stops if anything else is staged. Output goes to `logs/refresh.log`.

OpenReview refuses anonymous API requests, so the script needs a login. Put it in a `.env` file in this folder (git ignores it):

```sh
EMAIL=you@example.com
PASSWORD=your-openreview-password
```

To run it on a schedule on macOS, edit the path and hours in `tools/com.dipta007.rebuttal-radar.plist`, then:

```sh
cp tools/com.dipta007.rebuttal-radar.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.dipta007.rebuttal-radar.plist
```

## Past-year table

`docs/data/history.json` holds counts by starting rank for ICLR 2024 and 2025. To rebuild it, download the per-review rating files from [papercopilot/iclr-insights](https://github.com/papercopilot/iclr-insights) and the paper lists from [papercopilot/paperlists](https://github.com/papercopilot/paperlists) into `previous/` (git ignores it), then:

```sh
uv run --no-project python tools/build_history.py previous docs/data/history.json
```

## Findings page

`docs/findings.html` answers ten questions about the rebuttal, sorted with the most surprising first. Its data, `docs/data/findings.json`, holds totals only: no paper and no reviewer is listed. To rebuild it from the newest raw snapshot, the per-snapshot summaries, and the past-year files (see the next section):

```sh
uv run --no-project python tools/build_findings.py snapshots/<newest snapshot id> state/snapshots previous docs/data/findings.json
```

## Tests

```sh
uv run --no-project python tests/test_pipeline.py
bash tests/test_refresh.sh
```

The tests use synthetic data and make no network calls. `tests/page_check.md` lists what to check by eye after a page change.
