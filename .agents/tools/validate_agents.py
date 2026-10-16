#!/usr/bin/env python3
"""Validate .agents/ frontmatter against STRICT_AGENT_POLICY requirements."""

from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

REQUIRED = {"name", "description", "owner", "allowed_tools", "review_required", "disabled", "tests"}
TARGETS = [".agents/agents/*.agent.md", ".agents/skills/*/SKILL.md"]

errors: list[str] = []

for pattern in TARGETS:
    for path in glob.glob(pattern):
        text = Path(path).read_text()
        if not text.startswith("---\n"):
            errors.append(f"{path}: missing opening frontmatter delimiter")
            continue
        end = text.find("\n---\n", 4)
        if end == -1:
            errors.append(f"{path}: missing closing frontmatter delimiter")
            continue
        fm = text[4:end]
        keys: set[str] = set()
        for line in fm.splitlines():
            if ":" in line:
                keys.add(line.split(":", 1)[0].strip())
        missing = REQUIRED - keys
        if missing:
            errors.append(f"{path}: missing frontmatter fields: {', '.join(sorted(missing))}")
        # basic non-empty checks
        for key in ("name", "description", "owner"):
            m = re.search(rf"^{key}:\s*(.+)$", fm, re.M)
            if not m or not m.group(1).strip():
                errors.append(f"{path}: empty '{key}'")
        # review_required must be true
        m = re.search(r"^review_required:\s*(.+)$", fm, re.M)
        if m and m.group(1).strip().lower() not in ("true",):
            errors.append(f"{path}: review_required must be true")
        # disabled must be false
        m = re.search(r"^disabled:\s*(.+)$", fm, re.M)
        if m and m.group(1).strip().lower() not in ("false",):
            errors.append(f"{path}: disabled must be false")

# Check context dir exists
if not Path(".agents/context").is_dir():
    errors.append(".agents/context/: directory missing")

# Check required commands
for p in ("storage-update.prompt.md", "create-service.prompt.md", "quality-loop.prompt.md"):
    if not Path(".agents/commands", p).is_file():
        errors.append(f".agents/commands/{p}: missing")

if errors:
    print("AGENTS POLICY CHECK FAILED:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print(f"AGENTS POLICY CHECK PASSED ({sum(len(glob.glob(p)) for p in TARGETS)} files validated)")
