# Page check list

Design choices: Bricolage Grotesque for headings, Atkinson Hyperlegible for text (chosen for easy reading). Blue `#2a78d6` means up or now, orange `#eb6834` means down, gray means the first snapshot. The pair passes the color-blind validator in light and dark. The one bold element is the rank strip in the lookup.

Check after any page change, in light and dark, at desktop width and at 390 px:

- [ ] One snapshot only: tiles show 0, the note says the first update has not run, the movers list shows its empty message.
- [ ] Lookup by number shows scores, rank range, the three facts, the what-if, and the past-year table.
- [ ] A paper with no first-snapshot scores shows "had no scores" and no first-snapshot line.
- [ ] A title search with many matches lists 8 and says how many more match.
- [ ] An unknown number or title shows the "may also be withdrawn or desk-rejected" message.
- [ ] With `data/history.json` missing, everything else works and the past-year block says it is not available.
- [ ] No console errors from the page. No horizontal scroll.
