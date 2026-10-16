import re, glob, os

REQUIRED = ["owner", "allowed_tools", "review_required", "disabled", "tests"]

def parse_keys(fm):
    keys = set()
    for line in fm.splitlines():
        if ":" in line:
            keys.add(line.split(":", 1)[0].strip())
    return keys

def default_tools(path, fm):
    # agents have tools: [...]
    m = re.search(r"^tools:\s*(.+)$", fm, re.M)
    if m:
        return m.group(1).strip()
    # skills: decide by name/keywords
    name = ""
    nm = re.search(r"^name:\s*(.+)$", fm, re.M)
    if nm:
        name = nm.group(1).lower()
    text = (path + " " + name).lower()
    exec_keywords = ["deploy", "migration", "quality", "storage", "auth", "execute", "run", "build", "flash", "debug", "alembic", "backend-quality"]
    if any(k in text for k in exec_keywords):
        return "[read, search, edit, execute]"
    return "[read, search, edit]"

def default_tests(path, fm):
    name = ""
    nm = re.search(r"^name:\s*(.+)$", fm, re.M)
    if nm:
        name = nm.group(1).lower()
    text = (path + " " + name).lower()
    if "core-ai" in text or "core ai" in text:
        return '"uv run pytest -q src/app/core/core_ai/tests"'
    if "db-migration" in text or "alembic" in text or "migration" in text:
        return '"just test-integration"'
    if "quality" in text:
        return '"just lint"'
    if "test-engineer" in text or "test engineer" in text:
        return '"just test"'
    return '"just test-unit"'

files = []
files += glob.glob(".agents/agents/*.agent.md")
files += glob.glob(".agents/skills/*/SKILL.md")

for f in files:
    with open(f) as fh:
        content = fh.read()
    if not content.startswith("---\n"):
        print("SKIP (no frontmatter):", f)
        continue
    # find closing ---
    end = content.find("\n---\n", 4)
    if end == -1:
        # maybe \n--- at end
        end = content.find("\n---", 4)
    if end == -1:
        print("SKIP (no closing):", f)
        continue
    fm = content[4:end]
    keys = parse_keys(fm)
    # build additions
    additions = []
    if "owner" not in keys:
        additions.append("owner: team/backend")
    if "allowed_tools" not in keys:
        additions.append(f"allowed_tools: {default_tools(f, fm)}")
    if "review_required" not in keys:
        additions.append("review_required: true")
    if "disabled" not in keys:
        additions.append("disabled: false")
    if "tests" not in keys:
        additions.append(f"tests: {default_tests(f, fm)}")
    if not additions:
        print("OK (already complete):", f)
        continue
    new_fm = fm.rstrip("\n") + "\n" + "\n".join(additions) + "\n"
    new_content = "---\n" + new_fm + "---\n" + content[end+5:]  # after closing ---\n
    # content[end+5:] skips "\n---\n" (5 chars? \n---\n =5) yes
    with open(f, "w") as fh:
        fh.write(new_content)
    print("UPDATED:", f, "->", additions)

print("DONE")
