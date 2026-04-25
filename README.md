# repo-onboarding-agent

Point it at a repo. Get a structured onboarding brief in seconds.

Drop a new agent into an unfamiliar codebase and the first 20 minutes vanish into ritual: find the entry points, decode the test commands, figure out which files are haunted. This agent does that analysis once and produces a report every subsequent session can skip straight past.

Here's what the output contains:

- Overview — what the project does, its stack, scale, and CI setup
- Tech Stack — all framework and library versions in a dependency table
- Directory Map — annotated file tree with a description of every significant path
- Key Commands — every runnable command from Makefile / pyproject.toml / package.json / Justfile, classified by purpose
- Test Setup — how to run tests, key fixtures, coverage baseline, any test-DB requirements
- Risky Areas — auth code, zero-coverage modules, fragile integrations — each with a risk level and a recommendation
- Entry Points — the 2–3 files to read first and exactly why each one unlocks the rest
- First Good Tasks — scoped starter tasks with file lists, complexity estimates, and acceptance criteria
- Open Questions — unresolved ambiguities worth discussing before touching sensitive areas

See [reports/examples/example-report.md](reports/examples/example-report.md) for a realistic full output.

## Usage

```bash
python examples/run_onboarding.py --repo /path/to/project
```

Pass `--output reports/my-project.md` to set a custom output path. The report is also printed to stdout as a summary.

```
$ python examples/run_onboarding.py --repo ~/src/inventory-api

[1/6] Scanning directory structure...    ✓  47 directories, 312 files
[2/6] Inferring tech stack...            ✓  Python · FastAPI · PostgreSQL
[3/6] Extracting commands...             ✓  13 commands (Makefile + pyproject.toml)
[4/6] Mapping entry points...            ✓  3 entry points identified
[5/6] Detecting risky areas...           ✓  4 areas flagged
[6/6] Suggesting first good tasks...     ✓  3 tasks suggested

Report written to: reports/inventory-api-onboarding.md
```

Hand the report to any agent at session start and it already knows the test command, the relevant router, the risky auth middleware it should not touch, and which module has zero coverage.

## Report sections

| Section | What it contains |
|---|---|
| Overview | Plain-language description of the project, tech choices, scale, and deployment target |
| Tech Stack | Framework and library versions in a structured table |
| Directory Map | Annotated file tree with one-line descriptions of every significant directory and file |
| Key Commands | Every runnable command from Makefile, pyproject.toml, package.json, Justfile — with dev / test / deploy classification |
| Test Setup | How to run tests, which fixtures exist, coverage percentage, any test-DB setup required |
| Risky Areas | Files flagged for no coverage, auth / billing / crypto patterns, incident-correlated commits, or missing retry logic — each with a risk level and concrete recommendation |
| Entry Points | The 2–3 files a new contributor should read first, with a sentence on why each one unlocks the rest |
| First Good Tasks | 2–4 scoped starter tasks with file lists, complexity estimates, and clear acceptance criteria |
| Open Questions | Ambiguities or known gaps worth surfacing before any significant work begins |

## How it works

- **Structure analyzer** — walks the repo tree, reads dependency manifests, and infers tech stack, directory conventions, and project scale
- **Command extractor** — parses Makefile targets, pyproject.toml scripts, package.json scripts, and Justfile rules into a unified command inventory with semantic labels
- **Risk identifier** — applies static heuristics: zero-test-coverage detection, auth/crypto/billing keyword matching, dependency graph density, and comment-based signals like `# TODO` and `# FRAGILE`

## Extending it

- Add an analyzer by creating a new module under `src/analyzers/` that returns a typed dataclass, then register it in `src/agent.py`
- Override the report template in `templates/onboarding-report.md` to add, reorder, or rename sections without touching Python
- Wire an LLM call into the `first_good_tasks` and `open_questions` analyzers for the judgment-requiring sections — the stub interfaces are already defined

Design artifact and architectural sketch — the agent structure, data models, and report format are fully specified; the analyzer implementations are stubs ready to be filled with real static analysis logic.
