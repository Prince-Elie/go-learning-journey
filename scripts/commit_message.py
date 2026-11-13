#!/usr/bin/env python3
"""'[Sync Iteration] go/lasagna/2' -> 'feat(go/lasagna): iteration 2'"""
import re
import sys

title = " ".join(sys.argv[1:])
m = re.search(r"([\w-]+)/([\w-]+)(?:/(\d+))?\s*$", title)
if m:
    track, slug, it = m.groups()
    print(f"feat({track}/{slug}): " + (f"iteration {it}" if it else "solution"))
else:
    print(title or "feat: sync solution")
