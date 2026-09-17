#!/usr/bin/env python3
"""
Convert the remaining colour literals to design tokens.

Run from the frontend directory:

    python3 tokenise.py --dry-run
    python3 tokenise.py

Every literal is mapped by the role it plays rather than by its value, so a
grey used as a border becomes a line token and the same grey used as a panel
becomes a surface token. The palette was applied consistently enough that the
value alone is a reliable guide, but the mapping is grouped by intent so the
next person can see why each choice was made.

BOSS-branded views are skipped. That portal carries its own palette
deliberately and its literals are already expressed as --boss-* tokens where
they matter; rewriting them against the staff palette would be wrong.
"""
import argparse
import glob
import os
import re

# Views and components belonging to the public portal. Their colours are the
# BOSS identity and are not the staff palette in disguise.
SKIP = {
    "ReaderHome.vue", "ReaderArticle.vue", "ReaderLoginView.vue",
    "ReaderRegisterView.vue", "IssueArchive.vue", "IssueReader.vue",
    "AboutView.vue", "LegalView.vue", "SavedArticles.vue",
    "BossShell.vue", "CookieNotice.vue", "Paywall.vue",
    "FlipbookReader.vue", "BookmarkButton.vue", "StaffLoginView.vue",
}

MAPPING = {
    # ---- brand ----------------------------------------------------------
    "#1a2744": "var(--nv-navy-2)",
    "#24365e": "var(--nv-navy-3)",
    "#2c3e63": "var(--nv-navy-3)",
    "#0d1526": "var(--nv-navy)",
    "#4a7fb5": "var(--nv-accent)",

    # Text tints used on the navy sidebar. They read as greys but they are
    # navy-derived, which is why they are not mapped to the neutral scale.
    "#9fb0cc": "var(--nv-accent)",
    "#b9c9e0": "var(--nv-accent)",
    "#7f8fab": "var(--nv-text-faint)",
    "#6f82a3": "var(--nv-text-faint)",
    "#5e6f8c": "var(--nv-text-muted)",

    # ---- informational --------------------------------------------------
    "#cfe0f5": "var(--info-line)",
    "#f6f9fd": "var(--info-bg)",
    "#e8f0fa": "var(--nv-accent-soft)",
    "#e4e9f0": "var(--nv-accent-soft)",
    "#e4e9ef": "var(--nv-accent-soft)",
    "#cdd8e8": "var(--nv-accent-soft)",

    # ---- warning --------------------------------------------------------
    "#b5651d": "var(--warn)",
    "#d9963c": "var(--warn)",
    "#96631a": "var(--warn)",
    "#8a6321": "var(--warn)",
    "#a3561c": "var(--warn)",
    "#8a5a12": "var(--warn)",
    "#a87a2a": "var(--warn)",
    "#7a5a2a": "var(--warn)",
    "#f0d9b5": "var(--warn-line)",
    "#f0d9c9": "var(--warn-line)",

    # ---- error ----------------------------------------------------------
    "#c95757": "var(--bad)",
    "#b53b3b": "var(--bad)",
    "#c0392b": "var(--bad)",
    "#9e2f2f": "var(--bad)",
    "#a84a4a": "var(--bad)",
    "#7a3a3a": "var(--bad)",
    "#e09a9a": "var(--bad)",
    "#d98080": "var(--bad)",
    "#f0cfcf": "var(--bad-line)",
    "#fdeeee": "var(--bad-bg)",

    # ---- success --------------------------------------------------------
    "#2e9e63": "var(--ok)",
    "#1c6b45": "var(--ok)",
    "#4a9a6a": "var(--ok)",
    "#7a9a5a": "var(--ok)",
    "#c9e6d4": "var(--ok-line)",
    "#eef8f2": "var(--ok-bg)",
    "#f4fbf7": "var(--ok-bg)",

    # ---- surfaces -------------------------------------------------------
    # The near-whites are panels; the slightly darker greys are the page
    # behind them. Both collapse to two tokens, which is the point.
    "#fbfcfd": "var(--nv-surface)",
    "#f6f8fa": "var(--nv-surface)",
    "#f6f7f9": "var(--nv-surface)",
    "#f4f4f4": "var(--nv-bg)",
    "#f0f0f0": "var(--nv-bg)",
    "#f2f4f6": "var(--nv-bg)",
    "#eef0f3": "var(--nv-bg)",
    "#f4f6f8": "var(--nv-bg)",
    "#f4f5f7": "var(--nv-bg)",
    "#f0f2f5": "var(--nv-bg)",

    # ---- lines ----------------------------------------------------------
    "#eaecef": "var(--nv-line)",
    "#e8ebef": "var(--nv-line)",
    "#e4e7ec": "var(--nv-line)",
    "#dfe4ea": "var(--nv-line)",
    "#dde1e6": "var(--nv-line)",
    "#dde2e8": "var(--nv-line-strong)",
    "#d5dae0": "var(--nv-line-strong)",
    "#d3d9e0": "var(--nv-line-strong)",

    # ---- text -----------------------------------------------------------
    "#4a5a6a": "var(--nv-text-muted)",
    "#8a97a8": "var(--nv-text-faint)",
    "#8a939e": "var(--nv-text-faint)",
    "#ccd2d9": "var(--nv-text-faint)",
    "#c8ced6": "var(--nv-text-faint)",
    "#b4bcc6": "var(--nv-text-faint)",
}


def convert(path, dry_run):
    original = open(path, encoding="utf-8").read()
    s = original
    hits = {}

    for literal, token in MAPPING.items():
        # Case-insensitive, because CSS does not care and the tree is mixed.
        pattern = re.compile(re.escape(literal), re.IGNORECASE)
        n = len(pattern.findall(s))
        if n:
            s = pattern.sub(token, s)
            hits[literal] = n

    if s != original and not dry_run:
        open(path, "w", encoding="utf-8").write(s)

    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        print("Dry run — nothing will be written.\n")

    files = sorted(
        f for f in glob.glob("src/**/*.vue", recursive=True)
        if os.path.basename(f) not in SKIP
    )

    total_files, total_swaps = 0, 0
    for f in files:
        hits = convert(f, args.dry_run)
        if not hits:
            continue
        total_files += 1
        n = sum(hits.values())
        total_swaps += n
        print(f"  {n:>3}  {f}")

    print(f"\n{total_swaps} literals converted across {total_files} files")

    if not args.dry_run:
        print("\nWhat to check now:")
        print("  · Every staff screen in light mode, then dark")
        print("  · The reports, which held the most literals")
        print("  · The scanning overlay, which is the only animated surface")
        print("  · Confirm nothing reads as the wrong semantic colour — an")
        print("    error in amber or a warning in red would be a mis-mapping")


if __name__ == "__main__":
    main()
