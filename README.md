# repo-onboarding-agent

> An agent that reads an unfamiliar codebase and produces a structured onboarding brief: project map, key commands, risky areas, and first good tasks.

---

## Why it exists

Every time an agent — or a human — starts a new session in an unfamiliar codebase, the first 20 minutes disappear into the same ritual: find the entry points, decode the test commands, figure out which files are haunted, guess what "good first task" even means here. That work is repeatable. It can be done once, stored durably, and handed to the next agent (or engineer) as a structured brief.

`repo-onboarding-agent` does that one-time analysis and produces an **Onboarding Report** — a structured markdown document that front-loads orientation so any subsequent session can skip straight to productive work.

The durable-context insight: the report doesn't expire quickly. A codebase's directory shape, test commands, risky files, and entry points change slowly. Running the agent once per week (or on each significant merge) means every session starts informed.

---

## What makes it interesting

| Feature | What it does |
|---|---|
| **Structured output** | Report is machine-readable JSON + human-readable Markdown, so downstream agents can parse it or humans can read it |
| **Risky area detection** | Flags files with no test coverage, files last touched during incident commits, dense dependency graphs, auth/billing/crypto code |
| **First-good-task suggestions** | Scans open TODOs, small isolated modules, and clearly-scoped untested functions to suggest where to start |
| **Command inventory** | Extracts every runnable command from `Makefile`, `package.json`, `pyproject.toml`, `Justfile`, etc. and classifies them (build / test / lint / serve / deploy) |
| **Entry point map** | Identifies main modules, API routers, CLI entry points, and background workers |
| **Tech stack inference** | Detects languages, frameworks, databases, and infra from dependency files and config |

---

## Quickstart

```bash
# Install dependencies
pip install -r requirements.txt

# Run on the current directory
python examples/run_onboarding.py --repo .

# Run on any local repo path
python examples/run_onboarding.py --repo /path/to/some/project

# Output to a specific file
python examples/run_onboarding.py --repo /path/to/project --output reports/my-project.md
```

The report is written to `reports/` by default and printed to stdout as a summary.

---

## Example workflow

```
$ python examples/run_onboarding.py --repo ~/src/my-api

[1/6] Scanning directory structure...    ✓  47 directories, 312 files
[2/6] Inferring tech stack...            ✓  Python · FastAPI · PostgreSQL · Redis
[3/6] Extracting commands...             ✓  11 commands found (Makefile + pyproject.toml)
[4/6] Mapping entry points...            ✓  3 entry points identified
[5/6] Detecting risky areas...           ✓  6 areas flagged
[6/6] Suggesting first good tasks...     ✓  4 tasks suggested

Report written to: reports/my-api-onboarding.md
```

Then hand the report to any agent at session start:

```python
context = open("reports/my-api-onboarding.md").read()
agent.run(system_prompt=AGENT_PROMPT, context=context, task="Add rate limiting to the /search endpoint")
```

The agent already knows the test command, the relevant router file, the risky auth middleware it shouldn't touch, and that there are 0 tests for the search module. It can work without re-discovering any of that.

---

## Report structure

See [ONBOARDING.md](ONBOARDING.md) for a full description of every section.

See [reports/examples/example-report.md](reports/examples/example-report.md) for a realistic example output.

---

## What this demonstrates

- **Codebase analysis as an agent capability**: treating "understand this repo" as a first-class task, not ambient cognition
- **Structured reporting for agent handoff**: designing output that serves both humans and downstream agents
- **Risk surface detection**: static analysis heuristics that don't require running the code
- **Command inventory extraction**: multi-format parsing (Make, npm, Poetry, Just) with semantic classification
- **Durable context as a pattern**: the observation that orientation work is amortizable across many sessions

---

## Project layout

```
repo-onboarding-agent/
├── src/
│   ├── agent.py              # Core OnboardingAgent + data models
│   └── analyzers/
│       ├── structure.py      # Directory/file structure analysis
│       ├── commands.py       # Runnable command extraction
│       └── risks.py          # Risky area detection
├── templates/
│   └── onboarding-report.md  # Report template
├── reports/
│   └── examples/
│       └── example-report.md # Realistic example output
├── tests/
│   └── test_agent.py
├── examples/
│   └── run_onboarding.py
├── requirements.txt
└── pyproject.toml
```

---

## Honest status

This is a design artifact and architectural sketch, not production-ready software. The agent structure, data models, and report format are fully specified. The analyzer implementations are stubs — the interesting engineering work is in filling them in with real static analysis logic, and optionally wiring an LLM for the "first good tasks" and "open questions" sections where judgment is required.

The example report (`reports/examples/example-report.md`) is hand-authored to show the target quality. A real implementation would generate something close to it automatically.

