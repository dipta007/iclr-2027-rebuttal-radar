# ICLR 2027 Rebuttal Radar

See how ICLR 2027 review scores move during the rebuttal, and where your paper stands.

Site: https://dipta007.github.io/iclr-2027-rebuttal-radar/

## Credit

This project is a fork of [iclr-2027-scores](https://github.com/shiqiangw/iclr-2027-scores) by shiqiangw. The original [ICLR 2027 Scores](https://shiqiangw.github.io/iclr-2027-scores/) page, the download and build pipeline, and the first snapshot (Nov 6) are their work. This fork adds the rebuttal-period sections and the 12-hour refresh.

## What the page shows

- **Where does my paper stand now?** Type a paper number or title. You get the scores then and now, the rank as a range, why the rank moved, what one raised score would do, and what happened to similar papers in ICLR 2024 and 2025.
- **What moved.** How many papers went up, went down, got a different number of reviews, or left.
- **How much more will move.** The share of raised review scores so far, next to the final share in past years.
- **Papers that moved.** A searchable list with scores before and after.
- **Score distribution, then and now**, and the cut-offs for the top 5, 10, 25, and 50 percent.
- **Which scores move**, and which score groups lose the most papers.
- **All papers**, ranked by mean score.

## What is published

Only paper numbers, titles, OpenReview forum ids, and numeric scores. Review text, abstracts, authors, and reviewer ids are never copied, and `check_output()` in `build_site.py` stops the build if any other text reaches the page data. Withdrawn and desk-rejected papers are not listed.

Raw downloads hold review text. They stay in `snapshots/`, which git ignores. Per-paper summaries of each snapshot stay in `state/`, which git also ignores, so papers that later withdraw are not listed anywhere in the published data. Keep `state/`: the first-day summary in it is what every later update is compared with.

## How it is counted

- Only official reviews and their overall rating count.
- A paper "went up" if it has the same number of reviews as in the first snapshot and a higher mean. "Went down" is the same with a lower mean.
- Reviewer identities are not public, so scores are matched by sorted position inside each paper. Two opposite changes on one paper can hide each other.
- Scores go from 1 to 4, so many papers share a mean. A rank is therefore shown as a range.
- Past-year rates come from papers with a similar starting rank. They are not a prediction.

## Refresh every 12 hours

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

## Tests

```sh
uv run --no-project python tests/test_pipeline.py
bash tests/test_refresh.sh
```

The tests use synthetic data and make no network calls. `tests/page_check.md` lists what to check by eye after a page change.
