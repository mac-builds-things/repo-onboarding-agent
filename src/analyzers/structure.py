"""
Structure analyzer for repo-onboarding-agent.

Walks the repository file tree to produce:
  - An annotated directory map (path -> purpose)
  - File and line counts
  - Language breakdown
  - Tech stack detection (frameworks, databases, infra)
  - Git metadata (HEAD SHA, last commit date, commit velocity)

All detection is purely static (no code execution required).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from ..agent import EntryPoint, TechStackItem


# ---------------------------------------------------------------------------
# Known directory purposes
# ---------------------------------------------------------------------------

KNOWN_DIR_PURPOSES: dict[str, str] = {
    "src": "Primary source code",
    "app": "Application source (framework conventions vary)",
    "lib": "Shared library code",
    "tests": "Test suite",
    "test": "Test suite",
    "spec": "Test suite (RSpec convention)",
    "__tests__": "Test suite (Jest convention)",
    "docs": "Documentation",
    "scripts": "One-off and utility scripts",
    "migrations": "Database schema migrations",
    "db": "Database fixtures, seeds, and schema",
    "static": "Static assets served directly",
    "public": "Public web assets",
    "templates": "HTML/Jinja/Handlebars templates",
    "config": "Application configuration files",
    "infra": "Infrastructure-as-code (Terraform, CDK, Helm, etc.)",
    "deploy": "Deployment scripts and configs",
    "k8s": "Kubernetes manifests",
    "helm": "Helm chart",
    ".github": "GitHub Actions workflows and PR templates",
    ".circleci": "CircleCI configuration",
    "node_modules": "npm dependencies (do not edit)",
    ".venv": "Python virtual environment (do not edit)",
    "venv": "Python virtual environment (do not edit)",
    "dist": "Build output (generated)",
    "build": "Build output (generated)",
    "__pycache__": "Python bytecode cache (generated)",
    "alembic": "Alembic database migration environment",
    "fixtures": "Test fixtures and sample data",
    "seeds": "Database seed data",
    "workers": "Background job workers",
    "tasks": "Task definitions (Celery, ARQ, etc.)",
    "schemas": "Data validation schemas",
    "models": "Data models / ORM definitions",
    "routers": "API route handlers",
    "routes": "API route handlers",
    "views": "View layer (MVC pattern)",
    "controllers": "Controllers (MVC pattern)",
    "services": "Service layer / business logic",
    "repositories": "Data access layer",
    "middleware": "HTTP middleware",
    "utils": "Utility functions",
    "helpers": "Helper functions",
    "types": "Type definitions",
    "interfaces": "Interface definitions",
    "constants": "Application constants",
    "exceptions": "Custom exception classes",
    "errors": "Error definitions",
}

# ---------------------------------------------------------------------------
# Framework / stack detection rules
# ---------------------------------------------------------------------------

# Each rule: (dependency_name_fragment, role, framework_display_name)
DEPENDENCY_RULES: list[tuple[str, str, str]] = [
    ("fastapi", "web framework", "FastAPI"),
    ("flask", "web framework", "Flask"),
    ("django", "web framework", "Django"),
    ("starlette", "web framework", "Starlette"),
    ("litestar", "web framework", "Litestar"),
    ("tornado", "web framework", "Tornado"),
    ("sanic", "web framework", "Sanic"),
    ("aiohttp", "web framework", "aiohttp"),
    ("express", "web framework", "Express"),
    ("next", "web framework", "Next.js"),
    ("rails", "web framework", "Rails"),
    ("sinatra", "web framework", "Sinatra"),
    ("gin-gonic", "web framework", "Gin"),
    ("echo", "web framework", "Echo"),
    ("sqlalchemy", "ORM", "SQLAlchemy"),
    ("alembic", "migrations", "Alembic"),
    ("tortoise-orm", "ORM", "Tortoise ORM"),
    ("peewee", "ORM", "Peewee"),
    ("prisma", "ORM", "Prisma"),
    ("sequelize", "ORM", "Sequelize"),
    ("psycopg2", "database driver", "PostgreSQL"),
    ("asyncpg", "database driver", "PostgreSQL (async)"),
    ("pymysql", "database driver", "MySQL"),
    ("motor", "database driver", "MongoDB (async)"),
    ("pymongo", "database driver", "MongoDB"),
    ("redis", "cache/queue", "Redis"),
    ("celery", "task queue", "Celery"),
    ("arq", "task queue", "arq"),
    ("dramatiq", "task queue", "Dramatiq"),
    ("rq", "task queue", "RQ"),
    ("pytest", "test runner", "pytest"),
    ("unittest", "test runner", "unittest"),
    ("jest", "test runner", "Jest"),
    ("vitest", "test runner", "Vitest"),
    ("pydantic", "validation", "Pydantic"),
    ("marshmallow", "validation", "Marshmallow"),
    ("httpx", "HTTP client", "HTTPX"),
    ("requests", "HTTP client", "Requests"),
    ("openai", "AI/LLM client", "OpenAI SDK"),
    ("anthropic", "AI/LLM client", "Anthropic SDK"),
    ("langchain", "AI/LLM framework", "LangChain"),
    ("uvicorn", "ASGI server", "Uvicorn"),
    ("gunicorn", "WSGI server", "Gunicorn"),
    ("hypercorn", "ASGI server", "Hypercorn"),
]


# ---------------------------------------------------------------------------
# StructureAnalyzer
# ---------------------------------------------------------------------------


class StructureAnalyzer:
    """
    Analyzes the directory structure and file contents of a repository to
    produce metadata, tech stack inferences, and a directory map.

    This class is intended to be instantiated once per repository and used
    by OnboardingAgent during the analysis pipeline.
    """

    # Directories to skip entirely during the walk
    SKIP_DIRS: frozenset[str] = frozenset(
        {
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            ".env",
            "dist",
            "build",
            ".next",
            ".nuxt",
            "coverage",
            ".coverage",
            ".mypy_cache",
            ".ruff_cache",
            ".pytest_cache",
            ".tox",
        }
    )

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path

    def analyze(self) -> StructureResult:
        """
        Walk the repository and produce a StructureResult.

        Steps:
          1. Walk the file tree (skipping SKIP_DIRS)
          2. Tally file counts and line counts by extension
          3. Annotate top-level and second-level directories
          4. Parse dependency files to infer tech stack
          5. Read git metadata (HEAD SHA, log)
          6. Detect entry point candidates

        Returns:
            StructureResult populated with all discovered information.
        """
        raise NotImplementedError(
            "StructureAnalyzer.analyze() is not yet implemented."
        )

    def _annotate_directory(self, rel_path: str) -> str:
        """
        Return a one-line purpose annotation for a directory path.

        Checks known directory name patterns first; falls back to a generic
        description based on what files it contains.
        """
        name = Path(rel_path).name
        return KNOWN_DIR_PURPOSES.get(name, "")

    def _detect_tech_stack(self, dep_files: dict[str, str]) -> list[TechStackItem]:
        """
        Parse dependency files and return a list of detected TechStackItems.

        Args:
            dep_files: Mapping of filename to file contents for all dependency
                       files found in the repo root.

        Returns:
            List of TechStackItem instances, deduplicated, ordered by role.
        """
        raise NotImplementedError("_detect_tech_stack() is not yet implemented.")

    def _get_git_metadata(self) -> dict:
        """
        Extract HEAD SHA, last commit date, and commit velocity from git log.

        Returns a dict with keys: sha, last_commit_date, commits_per_week.
        Returns empty dict if the repo is not a git repository or git is unavailable.
        """
        raise NotImplementedError("_get_git_metadata() is not yet implemented.")

    def _detect_entry_points(self) -> list[EntryPoint]:
        """
        Scan for likely entry points: main.py, app.py, CLI scripts,
        FastAPI/Flask app objects, Celery app instances, etc.
        """
        raise NotImplementedError("_detect_entry_points() is not yet implemented.")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


from dataclasses import dataclass, field


@dataclass
class StructureResult:
    """Output of StructureAnalyzer.analyze()."""

    file_count: int = 0
    line_count: int = 0
    language_breakdown: dict[str, int] = field(default_factory=dict)
    """Maps language name to line count."""

    directory_map: dict[str, str] = field(default_factory=dict)
    """Maps relative directory path to one-line purpose annotation."""

    dependency_files_found: list[str] = field(default_factory=list)
    """Names of dependency/config files found in the repo root."""

    tech_stack: list[TechStackItem] = field(default_factory=list)
    entry_points: list[EntryPoint] = field(default_factory=list)

    git_sha: Optional[str] = None
    last_commit_date: Optional[str] = None
    commit_velocity: Optional[str] = None

    primary_language: str = "unknown"
    license: Optional[str] = None
    project_name: Optional[str] = None
    project_description: Optional[str] = None
