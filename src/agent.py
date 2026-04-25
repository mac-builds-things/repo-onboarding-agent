"""
Core agent module for repo-onboarding-agent.

Defines the primary data models and the OnboardingAgent orchestrator that
coordinates the individual analyzers into a unified onboarding report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class RiskCategory(str, Enum):
    """Categories of risky areas detected in a codebase."""

    AUTH = "auth"
    BILLING = "billing"
    CRYPTO = "crypto"
    NO_TESTS = "no-tests"
    HIGH_CHURN = "high-churn"
    LARGE_FILE = "large-file"
    COMPLEX_DEPS = "complex-deps"
    INCIDENT_TOUCHED = "incident-touched"
    GOD_OBJECT = "god-object"
    ENV_ACCESS = "env-access"


class TaskEffort(str, Enum):
    """Estimated effort level for a suggested first task."""

    SMALL = "S"
    MEDIUM = "M"
    LARGE = "L"


class CommandCategory(str, Enum):
    """Semantic category of a runnable command."""

    INSTALL = "install"
    DEV = "dev"
    TEST = "test"
    LINT = "lint"
    BUILD = "build"
    DATABASE = "database"
    DEPLOY = "deploy"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class RiskyArea(BaseModel):
    """A file or module that warrants extra care before modification."""

    path: str = Field(description="Relative path from repo root")
    category: RiskCategory
    reason: str = Field(description="Human-readable explanation of why this area is risky")
    recommended_action: str = Field(
        description="What to do before touching this file (e.g., 'add tests first', 'consult owner')"
    )
    severity: int = Field(
        default=2,
        ge=1,
        le=3,
        description="1=low, 2=medium, 3=high",
    )


class FirstGoodTask(BaseModel):
    """A suggested task for a new contributor to build familiarity."""

    title: str
    why: str = Field(description="Why this is a good first task (isolated, well-scoped, low blast radius)")
    files: list[str] = Field(description="Relevant file paths")
    effort: TaskEffort
    hint: Optional[str] = Field(default=None, description="Optional implementation hint")


class Command(BaseModel):
    """A runnable command extracted from the repo."""

    name: str = Field(description="Short identifier, e.g. 'test', 'dev', 'migrate'")
    command: str = Field(description="The actual shell command string")
    category: CommandCategory
    source: str = Field(description="Where this was found, e.g. 'Makefile', 'package.json'")
    description: Optional[str] = Field(default=None)


class EntryPoint(BaseModel):
    """A primary execution entry point into the system."""

    kind: str = Field(description="'api', 'cli', 'worker', 'main', 'cron'")
    path: str
    description: str
    symbol: Optional[str] = Field(default=None, description="Function or class name if applicable")


class TechStackItem(BaseModel):
    """A single item in the detected tech stack."""

    name: str
    version: Optional[str] = None
    role: str = Field(description="e.g. 'web framework', 'database', 'test runner'")
    confidence: str = Field(default="high", description="'high' | 'medium' | 'low'")


class OnboardingReport(BaseModel):
    """
    The full structured onboarding brief for a repository.

    This is the primary output of OnboardingAgent.analyze_repo().
    It can be serialized to JSON or rendered to Markdown via a template.
    """

    # Metadata
    repo_name: str
    repo_path: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    agent_version: str = "0.1.0"
    git_sha: Optional[str] = None

    # Content sections
    project_overview: str = Field(description="1–2 paragraph description of what the project does")
    primary_language: str
    license: Optional[str] = None
    last_commit_date: Optional[str] = None
    commit_velocity: Optional[str] = Field(default=None, description="e.g. '~8 commits/week'")
    file_count: int = 0
    line_count: int = 0

    tech_stack: list[TechStackItem] = Field(default_factory=list)
    directory_map: dict[str, str] = Field(
        default_factory=dict,
        description="path -> one-line purpose annotation",
    )
    commands: list[Command] = Field(default_factory=list)
    entry_points: list[EntryPoint] = Field(default_factory=list)
    risky_areas: list[RiskyArea] = Field(default_factory=list)
    first_good_tasks: list[FirstGoodTask] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    test_framework: Optional[str] = None
    test_command: Optional[str] = None
    test_file_count: int = 0

    def to_json(self, indent: int = 2) -> str:
        """Serialize the report to a JSON string."""
        return self.model_dump_json(indent=indent)

    def summary(self) -> str:
        """Return a short human-readable summary suitable for console output."""
        lines = [
            f"  Repo:          {self.repo_name}",
            f"  Language:      {self.primary_language}",
            f"  Files:         {self.file_count}",
            f"  Commands:      {len(self.commands)}",
            f"  Risky areas:   {len(self.risky_areas)}",
            f"  First tasks:   {len(self.first_good_tasks)}",
            f"  Open Qs:       {len(self.open_questions)}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class OnboardingAgent:
    """
    Orchestrates the analysis of an unfamiliar codebase and produces an
    OnboardingReport.

    The agent coordinates multiple specialized analyzers:
      - StructureAnalyzer  → directory map, file counts, tech stack
      - CommandAnalyzer    → key commands inventory
      - RiskAnalyzer       → risky area detection

    The entry point, first-good-task, and open-question sections are either
    derived from the above analyzers or (when an LLM client is provided)
    generated with an LLM-assisted reasoning pass.

    Usage::

        agent = OnboardingAgent(repo_path=Path("/path/to/repo"))
        report = agent.analyze_repo()
        print(report.summary())
        report_md = agent.render_markdown(report)
    """

    def __init__(
        self,
        repo_path: Path,
        *,
        llm_client=None,
        max_file_size_kb: int = 500,
        verbose: bool = False,
    ) -> None:
        self.repo_path = repo_path.resolve()
        self.llm_client = llm_client
        self.max_file_size_kb = max_file_size_kb
        self.verbose = verbose

    def analyze_repo(self) -> OnboardingReport:
        """
        Run the full analysis pipeline and return a structured OnboardingReport.

        Pipeline stages:
          1. Validate repo path and collect basic metadata
          2. Run StructureAnalyzer
          3. Run CommandAnalyzer
          4. Run RiskAnalyzer
          5. Derive entry points
          6. Generate first-good-task suggestions
          7. Collect open questions
          8. Assemble and return OnboardingReport
        """
        raise NotImplementedError(
            "analyze_repo() is not yet implemented. "
            "See src/analyzers/ for the individual analyzer stubs."
        )

    def render_markdown(self, report: OnboardingReport, template_path: Optional[Path] = None) -> str:
        """
        Render an OnboardingReport to a Markdown string using the report template.

        Args:
            report: The OnboardingReport to render.
            template_path: Optional path to a custom Jinja2 template. Defaults to
                           templates/onboarding-report.md relative to the package root.

        Returns:
            Rendered Markdown string.
        """
        raise NotImplementedError("render_markdown() is not yet implemented.")

    def save_report(
        self,
        report: OnboardingReport,
        output_dir: Path,
        *,
        formats: list[str] = None,
    ) -> dict[str, Path]:
        """
        Save the report in one or more formats (markdown, json).

        Args:
            report: The OnboardingReport to save.
            output_dir: Directory to write output files into.
            formats: List of format strings: 'markdown', 'json'. Defaults to ['markdown'].

        Returns:
            Dict mapping format name to the path of the written file.
        """
        raise NotImplementedError("save_report() is not yet implemented.")


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def analyze_repo(repo_path: str | Path, **kwargs) -> OnboardingReport:
    """
    Convenience function: create an OnboardingAgent and run the full analysis.

    Args:
        repo_path: Path to the repository root to analyze.
        **kwargs: Passed through to OnboardingAgent.__init__().

    Returns:
        A fully-populated OnboardingReport.

    Example::

        report = analyze_repo("/path/to/my-project", verbose=True)
        print(report.summary())
    """
    agent = OnboardingAgent(repo_path=Path(repo_path), **kwargs)
    return agent.analyze_repo()
