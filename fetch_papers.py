"""Fetch a researcher's publications from OpenAlex by ORCID.

Preprints that have a matching published version (same normalized title,
overlapping authors) are merged into that published entry: the published
entry keeps its own citation counts plus the preprint's, so no citations are
lost, and only one row appears per paper. Preprints with no published match
(not yet published) are kept as their own entries.

Saves the result to papers.json (machine-readable) and papers.xlsx
(human-readable, for checking the list is correct).

Usage:
    python -X utf8 fetch_papers.py <ORCID>
    python -X utf8 fetch_papers.py 0000-0003-4903-0318
"""

import json
import re
import sys
import time
from pathlib import Path

import requests
from openpyxl import Workbook

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
MAILTO = "genn@uw.edu"  # OpenAlex's polite pool: faster, more reliable responses
PER_PAGE = 200


def normalize_orcid(orcid):
    orcid = orcid.strip()
    if orcid.startswith("http"):
        return orcid
    return f"https://orcid.org/{orcid}"


def fetch_all_works(orcid):
    orcid_url = normalize_orcid(orcid)
    works = []
    cursor = "*"
    while cursor:
        params = {
            "filter": f"author.orcid:{orcid_url}",
            "per-page": PER_PAGE,
            "cursor": cursor,
            "mailto": MAILTO,
        }
        response = requests.get(OPENALEX_WORKS_URL, params=params, timeout=30)
        if response.status_code == 429:
            print("OpenAlex asked us to slow down, waiting a moment...")
            time.sleep(5)
            continue
        response.raise_for_status()
        payload = response.json()
        works.extend(payload["results"])
        cursor = payload["meta"].get("next_cursor")
        if not payload["results"]:
            break
    return works


def citations_by_year(work):
    return {
        str(entry["year"]): entry["cited_by_count"]
        for entry in work.get("counts_by_year", [])
    }


def coauthors(work):
    names = []
    for authorship in work.get("authorships", []):
        name = authorship.get("author", {}).get("display_name")
        if name:
            names.append(name)
    return names


def summarize(work):
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    venue = source.get("display_name")

    return {
        "title": work.get("title"),
        "year": work.get("publication_year"),
        "type": work.get("type"),
        "venue": venue,
        "doi": work.get("doi"),
        "link": work.get("id"),
        "cited_by_count": work.get("cited_by_count", 0),
        "citations_by_year": citations_by_year(work),
        "coauthors": coauthors(work),
        "merged_preprint_titles": [],
    }


def normalize_title(title):
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    return re.sub(r"\s+", " ", title).strip()


def shares_an_author(a, b):
    return bool(set(a["coauthors"]) & set(b["coauthors"]))


def merge_citations(published, preprint):
    for year, count in preprint["citations_by_year"].items():
        published["citations_by_year"][year] = published["citations_by_year"].get(year, 0) + count
    published["cited_by_count"] += preprint["cited_by_count"]
    published["merged_preprint_titles"].append(preprint["title"])


def merge_preprints_into_published(papers):
    published = [p for p in papers if p["type"] != "preprint"]
    preprints = [p for p in papers if p["type"] == "preprint"]

    by_title = {}
    for pub in published:
        by_title.setdefault(normalize_title(pub["title"]), []).append(pub)

    unmatched_preprints = []
    for preprint in preprints:
        candidates = by_title.get(normalize_title(preprint["title"]), [])
        match = next((c for c in candidates if shares_an_author(c, preprint)), None)
        if match:
            merge_citations(match, preprint)
        else:
            unmatched_preprints.append(preprint)

    return published + unmatched_preprints


def drop_duplicate_datasets(papers):
    """Drop dataset entries whose title repeats an article or preprint title.

    OpenAlex often indexes the same underlying work twice: once as the
    article/preprint and once as its deposited dataset. The dataset entry
    adds no new information once its title already appears elsewhere.
    """
    non_dataset_titles = {
        normalize_title(p["title"])
        for p in papers
        if p["type"] in ("article", "preprint")
    }
    return [
        p for p in papers
        if not (p["type"] == "dataset" and normalize_title(p["title"]) in non_dataset_titles)
    ]


def save_json(papers, path):
    path.write_text(json.dumps(papers, indent=2, ensure_ascii=False), encoding="utf-8")


def save_spreadsheet(papers, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Papers"
    ws.append(["Title", "Year", "Type", "Venue", "Co-authors", "Cited by", "Merged preprints", "Link"])
    for paper in papers:
        ws.append([
            paper["title"],
            paper["year"],
            paper["type"],
            paper["venue"],
            ", ".join(paper["coauthors"]),
            paper["cited_by_count"],
            "; ".join(paper["merged_preprint_titles"]),
            paper["link"],
        ])
    wb.save(path)


def summarize_types(papers):
    counts = {}
    for paper in papers:
        counts[paper["type"]] = counts.get(paper["type"], 0) + 1
    return counts


def main():
    if len(sys.argv) < 2:
        print("Usage: python -X utf8 fetch_papers.py <ORCID>")
        sys.exit(1)

    orcid = sys.argv[1]
    print(f"Fetching works for ORCID {orcid} from OpenAlex...")
    works = fetch_all_works(orcid)
    papers = [summarize(work) for work in works]
    total_before = len(papers)

    papers = merge_preprints_into_published(papers)
    papers = drop_duplicate_datasets(papers)
    papers.sort(key=lambda p: (p["year"] or 0), reverse=True)

    out_dir = Path(__file__).parent
    save_json(papers, out_dir / "papers.json")
    save_spreadsheet(papers, out_dir / "papers.xlsx")

    merged_count = sum(len(p["merged_preprint_titles"]) for p in papers)
    print(f"\nFetched {total_before} works, merged {merged_count} preprints into their published version.")
    print(f"{len(papers)} entries remain.")
    print("Breakdown by type:")
    for work_type, count in sorted(summarize_types(papers).items(), key=lambda x: -x[1]):
        print(f"  {work_type}: {count}")
    print("\nSaved papers.json and papers.xlsx.")


if __name__ == "__main__":
    main()
