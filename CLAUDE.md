# CLAUDE.md

## Project

Python 3.11+ repo onboarding agent. Analyzes an unfamiliar codebase and produces a structured 9-section markdown brief that helps a developer (or agent) get up to speed quickly.

**Key dependencies:** `pydantic`, `rich`, `pathspec`

**Core structure:**

| Path | Purpose |
|------|---------|
| `src/agent.py` | `OnboardingAgent` class; `analyze_repo()` is the main entry point |
| `src/analyzers/structure.py` | Builds a directory map of the target repo |
| `src/analyzers/commands.py` | Detects runnable commands (Makefile, package.json scripts, etc.) |
| `src/analyzers/risks.py` | Identifies risky areas in the target repo |
| `templates/onboarding-report.md` | Jinja-style template that defines report structure |
| `reports/examples/example-report.md` | Canonical example of a high-quality finished report |

---

## Commands

```bash
python -m pytest tests/                    # Run tests
python examples/run_onboarding.py <path>   # Analyze a repo
```

---

## Report sections

Every generated report must contain **all 9 sections**, in order:

1. **Overview** — one-paragraph summary of what the repo does
2. **Tech Stack** — languages, frameworks, key libraries
3. **Directory Map** — annotated tree of top-level directories
4. **Key Commands** — how to build, test, run, and deploy
5. **Test Setup** — how tests are structured and how to run them
6. **Risky Areas** — files/directories that deserve extra caution (see criteria below)
7. **Entry Points** — where execution actually starts
8. **First Good Tasks** — beginner-friendly issues with complexity estimates
9. **Open Questions** — things that can't be answered from static analysis alone

If a section would be empty, write **"None identified"** — never omit the section.

See `templates/onboarding-report.md` for the full template and `reports/examples/example-report.md` for the target quality level.

---

## What counts as a risky area

`src/analyzers/risks.py` flags the following as risky:

- `auth/` directories, or any file whose name contains `auth`, `token`, `jwt`, or `password`
- Files with **no corresponding test file**
- Files **over 500 lines**
- Directories that appear to contain **external API integrations**
- **Migration scripts**

---

## Conventions

- **Reports are snapshots.** They describe the repo as of the analysis date. Do not edit a delivered report; create a new one with an updated timestamp.
- **First Good Tasks** must include a complexity estimate: `Easy (< 2 hours)`, `Medium (half day)`, or `Hard (full day+)`.
- **Open Questions** should surface things that are genuinely ambiguous from static analysis — runtime behavior, deployment environment, team conventions, etc.
- **Never hallucinate.** If something can't be determined from the filesystem, write `"Unable to determine from static analysis"` rather than guessing.

---

## Agent notes

When running an onboarding analysis on a real repo, always invoke analyzers in this order:

1. `structure.py` — build the directory map first
2. `commands.py` — detect runnable commands
3. `risks.py` — identify risky areas last (it needs the structure context)

The example report at `reports/examples/example-report.md` is the reference for output quality. Match its level of specificity and annotation before considering a report done.
