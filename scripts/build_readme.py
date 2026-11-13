#!/usr/bin/env python3
"""
Builds the documentation of the repo from the solutions synced by Exercism.

- Finds every solved exercise in the repo (any folder named after an exercise slug).
- Groups them by concept, in Exercism's syllabus order.
- Writes README.md (progress, next steps, tree, journal) and concepts/<concept>.md.
- Keeps everything between the MANUAL markers of README.md untouched.

Standard library only. Run from the repo root:  python3 scripts/build_readme.py
"""
import json
import os
import re
import subprocess
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACK = os.environ.get("TRACK", "go")
CONFIG_URL = f"https://raw.githubusercontent.com/exercism/{TRACK}/main/config.json"
CACHE = ROOT / "data" / f"{TRACK}_config.json"
README = ROOT / "README.md"
CONCEPTS_DIR = ROOT / "concepts"
IGNORED = {".git", ".github", "scripts", "data", "concepts", "node_modules"}

MANUAL_START = "<!-- MANUAL:START -->"
MANUAL_END = "<!-- MANUAL:END -->"
DEFAULT_MANUAL = """## About me

Full-stack developer student learning Go, one exercise at a time.
Solutions are synced automatically from Exercism; everything below is generated.
"""


# ---------------------------------------------------------------- track data
def load_config():
    try:
        with urllib.request.urlopen(CONFIG_URL, timeout=15) as r:
            data = r.read().decode()
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(data)
        return json.loads(data)
    except Exception:
        return json.loads(CACHE.read_text())


def syllabus_order(cfg):
    """Topological order of concepts, following the learning exercises' prerequisites."""
    names = {c["slug"]: c["name"] for c in cfg["concepts"]}
    learning = [e for e in cfg["exercises"]["concept"] if e.get("status") != "deprecated"]
    deps = defaultdict(set)
    for ex in learning:
        for c in ex["concepts"]:
            deps[c].update(ex["prerequisites"])
    order, seen = [], set()

    def visit(c, stack=()):
        if c in seen or c in stack:
            return
        for d in sorted(deps.get(c, ())):
            visit(d, stack + (c,))
        seen.add(c)
        order.append(c)

    for ex in learning:  # config order is the intended syllabus order
        for c in ex["concepts"]:
            visit(c)
    return order, names


def build_catalog(cfg, order):
    """slug -> info (name, type, concept it belongs to, difficulty, prerequisites)."""
    rank = {c: i for i, c in enumerate(order)}
    catalog = {}
    for ex in cfg["exercises"]["concept"]:
        if ex.get("status") == "deprecated" or not ex["concepts"]:
            continue
        catalog[ex["slug"]] = dict(
            name=ex["name"], kind="learning", concept=ex["concepts"][0],
            teaches=ex["concepts"], prereqs=ex["prerequisites"], uses=[], difficulty=None)
    for ex in cfg["exercises"]["practice"]:
        if ex.get("status") == "deprecated":
            continue
        related = [c for c in ex.get("practices", []) + ex.get("prerequisites", []) if c in rank]
        # a practice exercise belongs to the last concept it needs: that's when it unlocks
        concept = max(related, key=rank.get) if related else "_first-steps"
        catalog[ex["slug"]] = dict(
            name=ex["name"], kind="practice", concept=concept, teaches=[],
            prereqs=ex.get("prerequisites", []), uses=ex.get("practices", []),
            difficulty=ex.get("difficulty"))
    return catalog


# ------------------------------------------------------------- repo scanning
def find_solutions(catalog):
    """slug -> path of the shallowest folder named after the slug that contains files."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel = Path(dirpath).relative_to(ROOT)
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORED and not d.startswith("."))
        name = rel.name
        if name in catalog and name not in found:
            has_files = any(files for _, _, files in os.walk(dirpath))
            if has_files:
                found[name] = rel
    return found


def count_iterations(path):
    p = ROOT / path
    numbered = [d for d in p.iterdir() if d.is_dir() and re.fullmatch(r"\d+", d.name)]
    return max(1, len(numbered))


def first_commit_date(path):
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%as", "--", str(path)],
            cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.split()
        return out[-1] if out else None
    except Exception:
        return None


# ---------------------------------------------------------------- rendering
def title(slug, names):
    return "First steps" if slug == "_first-steps" else names.get(slug, slug.replace("-", " ").title())


def link(path):
    return "./" + str(path).replace(" ", "%20")


def progress_bar(done, total, width=20):
    filled = round(width * done / total) if total else 0
    return "█" * filled + "░" * (width - filled) + f" {done}/{total}"


def render_tree(paths):
    tree = {}
    for p in sorted(paths, key=str):
        node = tree
        for part in p.parts:
            node = node.setdefault(part, {})
    lines = ["."]

    def walk(node, prefix=""):
        items = list(node.items())
        for i, (k, child) in enumerate(items):
            last = i == len(items) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{k}/")
            walk(child, prefix + ("    " if last else "│   "))

    walk(tree)
    return "\n".join(lines)


def next_steps(catalog, solved, order, limit=3):
    learned = {c for s in solved if catalog[s]["kind"] == "learning" for c in catalog[s]["teaches"]}
    learned.add("_first-steps")
    rank = {c: i for i, c in enumerate(order)}
    todo = []
    for slug, ex in catalog.items():
        if slug in solved or ex["kind"] != "learning":
            continue
        if set(ex["prereqs"]) <= learned:
            todo.append((rank.get(ex["concept"], 999), slug))
    # a practice exercise is suggested only once every concept it uses has been learned,
    # easiest first, then in syllabus order
    practice = sorted(
        (ex["difficulty"] or 9, rank.get(ex["concept"], -1), s)
        for s, ex in catalog.items()
        if s not in solved and ex["kind"] == "practice"
        and set(ex["prereqs"]) | set(ex["uses"]) <= learned
        # no concept metadata: only trust it if it's marked very easy
        and (ex["prereqs"] or ex["uses"] or (ex["difficulty"] or 9) <= 1))
    return [s for _, s in sorted(todo)[:limit]], [s for _, _, s in practice[:limit]]


def read_manual():
    if README.exists():
        m = re.search(re.escape(MANUAL_START) + r"(.*?)" + re.escape(MANUAL_END),
                      README.read_text(), re.S)
        if m:
            return m.group(1).strip("\n")
    return DEFAULT_MANUAL.strip("\n")


def main():
    cfg = load_config()
    order, names = syllabus_order(cfg)
    catalog = build_catalog(cfg, order)
    solved = find_solutions(catalog)

    learning_total = sum(1 for e in catalog.values() if e["kind"] == "learning")
    learning_done = sum(1 for s in solved if catalog[s]["kind"] == "learning")
    practice_done = len(solved) - learning_done
    concepts_done = {c for s in solved if catalog[s]["kind"] == "learning" for c in catalog[s]["teaches"]}

    by_concept = defaultdict(list)
    for slug in solved:
        by_concept[catalog[slug]["concept"]].append(slug)
    concept_seq = ["_first-steps"] + order

    dates = {s: first_commit_date(p) or date.today().isoformat() for s, p in solved.items()}

    # ---- concepts/<concept>.md
    CONCEPTS_DIR.mkdir(exist_ok=True)
    for old in CONCEPTS_DIR.glob("*.md"):
        old.unlink()
    for c in concept_seq:
        if not by_concept.get(c):
            continue
        rows = []
        for s in sorted(by_concept[c], key=lambda s: (catalog[s]["kind"] != "learning", s)):
            ex = catalog[s]
            rows.append(f"| [{ex['name']}](../{solved[s]}) | {ex['kind']} | "
                        f"{count_iterations(solved[s])} | {dates[s] or '—'} |")
        page = [f"# {title(c, names)}", "",
                f"Concept page on Exercism: https://exercism.org/tracks/{TRACK}/concepts/{c}"
                if c != "_first-steps" else "Exercises that need no specific concept.", "",
                "| Exercise | Type | Iterations | Solved on |", "|---|---|---|---|", *rows, "",
                "[← Back to README](../README.md)", ""]
        (CONCEPTS_DIR / f"{c}.md").write_text("\n".join(page))

    # ---- README.md
    learn_next, practice_next = next_steps(catalog, solved, order)
    out = [
        f"# Exercism Journey — {TRACK.capitalize()}", "",
        "> Tracking my progress learning Go, one exercise at a time.", "",
        MANUAL_START, read_manual(), MANUAL_END, "",
        "## Progress", "",
        "| | |", "|---|---|",
        f"| Learning exercises | `{progress_bar(learning_done, learning_total)}` |",
        f"| Concepts unlocked | `{progress_bar(len(concepts_done & set(order)), len(order))}` |",
        f"| Practice exercises solved | **{practice_done}** |",
        f"| Last update | {date.today().isoformat()} |", "",
        "## Next up", "",
    ]
    out += [f"- 📘 **{catalog[s]['name']}** — learning `{catalog[s]['concept']}`" for s in learn_next]
    out += [f"- 🛠️ {catalog[s]['name']} — practice" for s in practice_next]
    if not (learn_next or practice_next):
        out.append("- Track complete 🎉")
    out += ["", "## Solutions by concept", "",
            "| # | Concept | Exercises |", "|---|---|---|"]
    n = 0
    for c in concept_seq:
        if not by_concept.get(c):
            continue
        n += 1
        items = sorted(by_concept[c], key=lambda s: (catalog[s]["kind"] != "learning", s))
        cells = ", ".join(("📘 " if catalog[s]["kind"] == "learning" else "🛠️ ")
                          + f"[{catalog[s]['name']}]({link(solved[s])})" for s in items)
        out.append(f"| {n} | [{title(c, names)}](./concepts/{c}.md) | {cells} |")
    if not n:
        out.append("| — | Nothing synced yet | — |")

    journal = sorted(((d, s) for s, d in dates.items() if d), reverse=True)[:15]
    out += ["", "📘 learning exercise · 🛠️ practice exercise", "", "## Journal", ""]
    out += [f"- `{d}` — {catalog[s]['name']}" for d, s in journal] or ["- Nothing yet."]
    out += ["", "## Repository tree", "", "```", render_tree(solved.values()), "```", "",
            "---", "<sub>Generated by `scripts/build_readme.py` after every sync. "
            "Edit only the section between the MANUAL markers.</sub>", ""]
    README.write_text("\n".join(out))
    print(f"{len(solved)} solutions, {learning_done}/{learning_total} learning exercises")


if __name__ == "__main__":
    main()
