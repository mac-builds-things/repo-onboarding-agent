# AGENTS.md

If you're an agent starting work in this repo, read this first.

---

## What this tool does

This is a **repo onboarding agent** — it generates structured, 9-section markdown briefs for unfamiliar codebases. Given a path to any local repository, it analyzes the filesystem and produces a report that helps a developer (or another agent) get oriented quickly: what the repo does, how to run it, where the risky code lives, and what to tackle first.

---

## How to run it

```bash
python examples/run_onboarding.py <path-to-repo>
```

Pass any local repo path. The agent will write a markdown report to `reports/` by default.

---

## What the output looks like

A 9-section markdown report:

1. Overview
2. Tech Stack
3. Directory Map
4. Key Commands
5. Test Setup
6. Risky Areas
7. Entry Points
8. First Good Tasks
9. Open Questions

See `reports/examples/example-report.md` for a full example at the expected quality level. Every section must be present — use "None identified" for empty ones rather than skipping them.

---

## How to extend it

Add new analyzers in `src/analyzers/`. Follow the existing patterns:

- Return typed results using `pydantic` dataclasses (see `CommandEntry` and `RiskyArea` for reference)
- Register your analyzer in `src/agent.py` inside `OnboardingAgent.analyze_repo()`
- Wire the output into the appropriate section in `templates/onboarding-report.md`

The three existing analyzers (`structure.py`, `commands.py`, `risks.py`) are the canonical examples of how analyzers are structured.

---

## Key invariants

- **Reports are immutable after delivery.** Never edit a report that has already been handed off. Create a new one with an updated timestamp instead.
- **Reports are point-in-time snapshots.** They describe the repo as of the moment of analysis. Stale reports are expected; they are not bugs.
- **No hallucination.** If the filesystem doesn't reveal something, write `"Unable to determine from static analysis"` — do not guess.

---

## Testing

Run the test suite before making any changes:

```bash
python -m pytest tests/
```

Tests are expected to be green on a clean checkout. If they are not, stop and investigate before proceeding.

---

## Where risky code lives in this repo

`src/analyzers/risks.py` is the most sensitive file in this codebase. Its job is to identify risky areas in *other* repos — which means it must be carefully calibrated to avoid false positives. Changes to risk detection logic require corresponding test coverage in `tests/`. Do not loosen or tighten detection heuristics without updating the tests.
