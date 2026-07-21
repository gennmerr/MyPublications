# Publications page

**Goal:** a web page of my published papers, with charts of how my citations
have grown over the years, published live so I can share it.

## Status: done — live at https://gennmerr.github.io/MyPublications/

## Steps

- [x] Create `MyPublications` repo, pushed to GitHub as public
- [x] Find my ORCID: `0000-0003-4903-0318` (confirmed by Gennifer)
- [x] Fetch my papers from OpenAlex, save as reusable script + `papers.json`
- [x] Check the fetched list is really mine
- [x] Design the page (interview, answers below)
- [x] Build `index.html`
- [x] Publish live with GitHub Pages
- [ ] Stretch: package as a `/publications-page` skill

## Design decisions

- **Vibe:** bold & colorful
- **Accent color:** teal/blue
- **Dark mode:** toggle (light/dark switch, not just system-following)
- **Featured stats:** total papers, years active
- **Charts:** cumulative citations over time, breakdown by work type
- **Papers list order:** most cited first
- **Per-paper details shown:** venue/journal only
- **Intro/bio blurb:** none — straight to stats and charts
- **Page title:** "Gennifer Merrihew"
- **List controls:** search box (filter papers by title/venue)

## Notes

- Fetch: 87 works from OpenAlex, 8 preprints merged into their published
  counterpart (citations combined, no data lost), 2 duplicate-titled datasets
  dropped. 77 entries remain in `papers.json` / `papers.xlsx`.
- Data check: automated first pass found no likely wrong-author entries;
  Gennifer reviewed the spreadsheet herself and approved the list.
- Preprint-merge and duplicate-dataset rules are baked into `fetch_papers.py`,
  so re-running it reproduces the same cleaned list.

(kept up to date as the work progresses, so it can be re-run later)
