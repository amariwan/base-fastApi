# Strenge Richtlinie für Skills, Agents und Copilot

Zweck
- Diese Richtlinie legt verbindliche, durchsetzbare Regeln für alle Skills, Agents und Copilot‑Instruktionen in diesem Repository fest. Ziel ist maximale Sicherheit, minimale Angriffsfläche und klare Review‑Prozeduren.

Geltungsbereich
- Gilt für alle Dateien unter `.github/skills`, `.github/agents`, `.github/prompts`, `.claude/skills`, `.claude/agents`, `.claude/prompts` sowie für `/.github/copilot-instructions.md`.

Grundprinzipien (unabdingbar)
1. Fail‑closed: Agents/Skills dürfen keine sensiblen oder unsicheren Aktionen ohne menschliche Freigabe ausführen.
2. Least privilege: Gewähre nur die minimal nötigen Tool‑Rechte (z. B. `read`, `search`).
3. Explizite Genehmigung: Jegliche Erweiterung von Toolberechtigungen (z. B. `edit`, `execute`, `run_in_terminal`) braucht eine dokumentierte Maintainer‑Genehmigung im PR.
4. Keine Geheimnisse: Keine API‑Keys, Passwörter, Tokens oder andere Secrets in Quelltext, Tests, Prompts oder Commits.
5. Keine Produktionsdaten: Keine Übertragung, Speicherung oder Nutzung echter PII/Produktionsdaten in Beispielen, Tests oder Prompt‑Aufzeichnungen.
6. Keine externen, unkontrollierten Netzwerkaufrufe: Requests an öffentliche APIs sind verboten, außer es existiert eine schriftliche Ausnahmeliste und ein Review‑Protokoll.
7. Keine destruktiven Aktionen: Löschen von Branches, automatische Migrationen gegen Produktionsdaten, direkte Deploys oder Docker‑Publishes sind verboten ohne menschliche Durchführung und 2‑stufige Verifikation.

Formale Anforderungen an jede Skill/Agent Datei
- YAML‑Frontmatter (Pflicht) mit mindestens diesen Feldern:
  - `name`: eindeutiger Name
  - `description`: kurze Zweckbeschreibung
  - `owner`: GitHub‑Team oder Benutzer
  - `allowed_tools`: Liste (z. B. `[read, search]`)
  - `review_required`: true
  - `disabled`: false (Default)
  - `tests`: narrowest validation command (z. B. `just test-unit --filter path`)

Beispiel‑Frontmatter:
---
name: example-skill
description: "Kurzbeschreibung"
owner: team/backend
allowed_tools: [read, search]
review_required: true
disabled: false
tests: "just test-unit -- path/to/tests"
---

Review‑ & Merge‑Prozess (Pflicht)
1. PR muss eine klare ‚Change‑Summary‘ mit Angabe der betroffenen Dateien, der minimalen Testbefehle und einer kurzen Risikobewertung enthalten.
2. Mindestens ein Maintainer‑Review ist erforderlich, plus ein spezieller Kommentar: `AI-POLICY: approved` vom Maintainer.
3. Vor Merge müssen die in `tests` genannten Befehle lokal oder in CI grün sein (z. B. `just test-unit`, `just check`).
4. Falls `allowed_tools` mehr als `read/search` enthält, ist zusätzlich ein Sicherheits‑Review mit freigegebenem Issue/PR‑Kommentar erforderlich.

Tests, Validierung und Nachvollziehbarkeit
- Jedes Feature/Änderung, die ein Agent/Skill vornimmt, benötigt begleitende Tests (Unit oder Integration) und die genauen Validierungsbefehle.
- Commit‑Nachricht und PR‑Beschreibung müssen eine kurze Audit‑Notiz enthalten: `AI-AUDIT: <one-line-reason>`.

Durchsetzung und Reaktion auf Vorfälle
- CI soll einen `ai-policy-check` Job implementieren (empfohlen). Bei Policy‑Verstößen: PR blockieren.
- Bei einem Vorfall muss der Skill/Agent sofort deaktiviert werden (`disabled: true`) und ein Issue `ai-policy-incident` mit Beschreibung und möglichen Folgen eröffnet werden.

Sanktionen
- Verstöße werden durch Revert, Issue‑Tracking und Codeowner‑Benachrichtigung behandelt. Wiederholte, schwerwiegende Verstöße führen zu Entzug der Merge‑Rechte für den Account, der die Änderung eingebracht hat.

Lizenz & Copyright
- Generierter oder vorgeschlagener Code muss Lizenz‑konform sein. Keine Aufnahme großer urheberrechtlich geschützter Textblöcke ohne Erlaubnis.

Minimaler Änderungsantrag (PR‑Checkliste)
- [ ] YAML‑Frontmatter vorhanden und ausgefüllt
- [ ] Beschreibung + Risikobewertung im PR
- [ ] `tests` definiert und lokal/CI grün
- [ ] Maintainer hat `AI-POLICY: approved` kommentiert
- [ ] Keine Secrets oder Produktionsdaten in PR

Kontakt
- Bei Unklarheiten: `@repo-maintainers` (Team in `owner`‑Feld)

Diese Richtlinie ist strikt: Änderungen an ihr selbst benötigen ein Maintainer‑Review und die gleiche Checkliste wie oben.
