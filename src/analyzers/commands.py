"""
Command analyzer for repo-onboarding-agent.

Extracts runnable commands from:
  - Makefile          (targets with ## comments for description)
  - package.json      (scripts section)
  - pyproject.toml    ([tool.taskipy.tasks], [tool.poe.tasks])
  - Justfile          (recipe names and docstrings)
  - Taskfile.yml      (task definitions)
  - CONTRIBUTING.md   (fenced code blocks that look like shell commands)

Each discovered command is classified into a CommandCategory and returned
as a Command model instance.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from ..agent import Command, CommandCategory


# ---------------------------------------------------------------------------
# Category classification heuristics
# ---------------------------------------------------------------------------

# Maps pattern -> category; evaluated in order, first match wins.
COMMAND_CATEGORY_PATTERNS: list[tuple[re.Pattern, CommandCategory]] = [
    (re.compile(r"\b(install|setup|bootstrap|init)\b", re.I), CommandCategory.INSTALL),
    (re.compile(r"\b(test|pytest|jest|vitest|rspec|go test|cargo test)\b", re.I), CommandCategory.TEST),
    (re.compile(r"\b(lint|ruff|flake8|pylint|eslint|mypy|pyright|tsc)\b", re.I), CommandCategory.LINT),
    (re.compile(r"\b(format|fmt|black|prettier|isort)\b", re.I), CommandCategory.LINT),
    (re.compile(r"\b(build|compile|bundle|webpack|rollup|esbuild|tsc)\b", re.I), CommandCategory.BUILD),
    (re.compile(r"\b(migrate|migration|alembic|flyway|liquibase|db:migrate)\b", re.I), CommandCategory.DATABASE),
    (re.compile(r"\b(seed|db:seed|fixtures)\b", re.I), CommandCategory.DATABASE),
    (re.compile(r"\b(deploy|release|publish|push|heroku|fly|vercel)\b", re.I), CommandCategory.DEPLOY),
    (re.compile(r"\b(dev|serve|start|run|watch|uvicorn|gunicorn|nodemon)\b", re.I), CommandCategory.DEV),
]


def classify_command(name: str, command: str) -> CommandCategory:
    """
    Classify a command into a CommandCategory based on its name and command string.

    Checks the command name first (more reliable), then the command body.
    Falls back to CommandCategory.OTHER if no pattern matches.
    """
    for pattern, category in COMMAND_CATEGORY_PATTERNS:
        if pattern.search(name) or pattern.search(command):
            return category
    return CommandCategory.OTHER


# ---------------------------------------------------------------------------
# Parser implementations (stubs)
# ---------------------------------------------------------------------------


def parse_makefile(content: str, source: str = "Makefile") -> list[Command]:
    """
    Parse a Makefile and extract documented targets.

    Recognizes the common pattern:

        target-name: deps  ## Description of the target
            recipe

    Also handles targets without ## comments, using the recipe body as the
    command string.

    Args:
        content: Raw Makefile content.
        source: Display name for the source file (default 'Makefile').

    Returns:
        List of Command instances.
    """
    raise NotImplementedError("parse_makefile() is not yet implemented.")


def parse_package_json(content: str, source: str = "package.json") -> list[Command]:
    """
    Parse a package.json file and extract the 'scripts' section.

    Args:
        content: Raw package.json content (JSON string).
        source: Display name for the source file.

    Returns:
        List of Command instances.
    """
    raise NotImplementedError("parse_package_json() is not yet implemented.")


def parse_pyproject_toml(content: str, source: str = "pyproject.toml") -> list[Command]:
    """
    Parse a pyproject.toml file and extract task definitions from:
      - [tool.taskipy.tasks]
      - [tool.poe.tasks]

    Args:
        content: Raw pyproject.toml content (TOML string).
        source: Display name for the source file.

    Returns:
        List of Command instances.
    """
    raise NotImplementedError("parse_pyproject_toml() is not yet implemented.")


def parse_justfile(content: str, source: str = "Justfile") -> list[Command]:
    """
    Parse a Justfile and extract recipe names and their bodies.

    Recognizes:
      - Recipe names followed by a colon
      - Docstring comments (lines starting with # before a recipe)

    Args:
        content: Raw Justfile content.
        source: Display name for the source file.

    Returns:
        List of Command instances.
    """
    raise NotImplementedError("parse_justfile() is not yet implemented.")


def parse_taskfile(content: str, source: str = "Taskfile.yml") -> list[Command]:
    """
    Parse a Taskfile.yml (Task runner) and extract task definitions.

    Args:
        content: Raw Taskfile.yml content (YAML string).
        source: Display name for the source file.

    Returns:
        List of Command instances.
    """
    raise NotImplementedError("parse_taskfile() is not yet implemented.")


# ---------------------------------------------------------------------------
# CommandAnalyzer
# ---------------------------------------------------------------------------


class CommandAnalyzer:
    """
    Scans a repository for command definition files and extracts all runnable
    commands with classification and deduplication.

    Usage::

        analyzer = CommandAnalyzer(repo_path=Path("/path/to/repo"))
        commands = analyzer.analyze()
    """

    # Files to look for, in priority order
    COMMAND_FILES: list[tuple[str, callable]] = [
        ("Makefile", parse_makefile),
        ("makefile", parse_makefile),
        ("GNUmakefile", parse_makefile),
        ("package.json", parse_package_json),
        ("pyproject.toml", parse_pyproject_toml),
        ("Justfile", parse_justfile),
        ("justfile", parse_justfile),
        ("Taskfile.yml", parse_taskfile),
        ("Taskfile.yaml", parse_taskfile),
    ]

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path

    def analyze(self) -> list[Command]:
        """
        Find all command definition files and parse each one.

        Returns:
            Deduplicated list of Command instances across all found sources,
            sorted by category then name.
        """
        raise NotImplementedError("CommandAnalyzer.analyze() is not yet implemented.")

    def _deduplicate(self, commands: list[Command]) -> list[Command]:
        """
        Remove duplicate commands.

        A command is considered a duplicate if it has the same name and command
        string as an already-seen command. When duplicates exist, the one from
        the higher-priority source file is kept.
        """
        seen: dict[str, Command] = {}
        for cmd in commands:
            key = f"{cmd.name}::{cmd.command}"
            if key not in seen:
                seen[key] = cmd
        return list(seen.values())
