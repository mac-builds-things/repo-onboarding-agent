"""
Tests for repo-onboarding-agent.

These are stub tests that define the intended behavior of the agent and its
analyzers. They are written in the style of executable specifications:
each test describes a contract that the implementation must satisfy.

Run with:
    pytest tests/ -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent import (
    Command,
    CommandCategory,
    FirstGoodTask,
    OnboardingAgent,
    OnboardingReport,
    RiskCategory,
    RiskyArea,
    TaskEffort,
    analyze_repo,
)
from src.analyzers.commands import classify_command
from src.analyzers.risks import RiskAnalyzer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """
    Create a minimal fake repository in a temp directory for testing.

    Structure:
        sample-repo/
        ├── app/
        │   ├── __init__.py
        │   ├── main.py
        │   ├── auth.py         <- should be flagged as auth risk
        │   └── utils.py        <- no corresponding test (no-tests risk)
        ├── tests/
        │   ├── __init__.py
        │   └── test_main.py
        ├── Makefile
        ├── requirements.txt
        └── pyproject.toml
    """
    repo = tmp_path / "sample-repo"
    repo.mkdir()

    # App source
    app = repo / "app"
    app.mkdir()
    (app / "__init__.py").write_text("")
    (app / "main.py").write_text(
        'from fastapi import FastAPI\napp = FastAPI()\n\n@app.get("/")\ndef root():\n    return {"status": "ok"}\n'
    )
    (app / "auth.py").write_text(
        "import jwt\n\ndef verify_token(token: str) -> dict:\n    return jwt.decode(token, 'secret', algorithms=['HS256'])\n"
    )
    (app / "utils.py").write_text(
        "def slugify(text: str) -> str:\n    return text.lower().replace(' ', '-')\n"
    )

    # Tests
    tests = repo / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")
    (tests / "test_main.py").write_text(
        "def test_root():\n    pass  # TODO: implement\n"
    )

    # Makefile
    (repo / "Makefile").write_text(
        "install:  ## Install dependencies\n\tpip install -e .\n\n"
        "test:  ## Run the test suite\n\tpytest -x\n\n"
        "lint:  ## Run ruff\n\truff check app/\n"
    )

    # Requirements
    (repo / "requirements.txt").write_text(
        "fastapi>=0.111.0\npydantic>=2.0\npytest>=8.0\nruff\njwt\n"
    )

    # pyproject.toml
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "sample-repo"\nversion = "0.1.0"\n'
    )

    return repo


# ---------------------------------------------------------------------------
# OnboardingReport model tests
# ---------------------------------------------------------------------------


class TestOnboardingReport:
    def test_report_can_be_instantiated_with_required_fields(self):
        report = OnboardingReport(
            repo_name="my-repo",
            repo_path="/tmp/my-repo",
            project_overview="A test repo.",
            primary_language="Python",
        )
        assert report.repo_name == "my-repo"
        assert report.primary_language == "Python"

    def test_report_serializes_to_json(self):
        report = OnboardingReport(
            repo_name="my-repo",
            repo_path="/tmp/my-repo",
            project_overview="A test repo.",
            primary_language="Python",
        )
        raw = report.to_json()
        parsed = json.loads(raw)
        assert parsed["repo_name"] == "my-repo"

    def test_summary_returns_string_with_key_fields(self):
        report = OnboardingReport(
            repo_name="my-repo",
            repo_path="/tmp/my-repo",
            project_overview="A test repo.",
            primary_language="Python",
            risky_areas=[
                RiskyArea(
                    path="app/auth.py",
                    category=RiskCategory.AUTH,
                    reason="Contains JWT logic",
                    recommended_action="Add tests first",
                )
            ],
        )
        summary = report.summary()
        assert "my-repo" in summary
        assert "Python" in summary
        assert "1" in summary  # 1 risky area

    def test_risky_area_severity_defaults_to_medium(self):
        area = RiskyArea(
            path="app/auth.py",
            category=RiskCategory.AUTH,
            reason="JWT logic",
            recommended_action="Review carefully",
        )
        assert area.severity == 2

    def test_risky_area_severity_is_bounded(self):
        with pytest.raises(Exception):
            RiskyArea(
                path="app/auth.py",
                category=RiskCategory.AUTH,
                reason="JWT logic",
                recommended_action="Review carefully",
                severity=5,  # out of range: should raise
            )

    def test_first_good_task_effort_enum_values(self):
        task = FirstGoodTask(
            title="Add missing tests",
            why="Isolated module, low blast radius",
            files=["app/utils.py"],
            effort=TaskEffort.SMALL,
        )
        assert task.effort == "S"


# ---------------------------------------------------------------------------
# Command classification tests
# ---------------------------------------------------------------------------


class TestCommandClassification:
    @pytest.mark.parametrize(
        "name, command, expected_category",
        [
            ("test", "pytest -x", CommandCategory.TEST),
            ("test-cov", "pytest --cov=app", CommandCategory.TEST),
            ("lint", "ruff check app/", CommandCategory.LINT),
            ("format", "ruff format app/", CommandCategory.LINT),
            ("typecheck", "mypy app/", CommandCategory.LINT),
            ("dev", "uvicorn app.main:app --reload", CommandCategory.DEV),
            ("start", "node server.js", CommandCategory.DEV),
            ("build", "docker build .", CommandCategory.BUILD),
            ("migrate", "alembic upgrade head", CommandCategory.DATABASE),
            ("db-seed", "python scripts/seed.py", CommandCategory.DATABASE),
            ("deploy", "fly deploy", CommandCategory.DEPLOY),
            ("install", "pip install -e .", CommandCategory.INSTALL),
            ("setup", "pip install -r requirements.txt", CommandCategory.INSTALL),
            ("docs", "mkdocs serve", CommandCategory.OTHER),
        ],
    )
    def test_classify_command(self, name, command, expected_category):
        assert classify_command(name, command) == expected_category


# ---------------------------------------------------------------------------
# RiskyArea detection tests
# ---------------------------------------------------------------------------


class TestRiskAnalyzer:
    def test_auth_file_is_flagged(self, sample_repo: Path):
        """A file named auth.py with JWT imports should be flagged as auth risk."""
        source_files = list((sample_repo / "app").glob("*.py"))
        analyzer = RiskAnalyzer(
            repo_path=sample_repo,
            source_files=source_files,
            test_file_paths=set((sample_repo / "tests").glob("test_*.py")),
        )
        with pytest.raises(NotImplementedError):
            analyzer.analyze()
        # TODO: Once implemented, assert:
        # areas = analyzer.analyze()
        # auth_areas = [a for a in areas if a.category == RiskCategory.AUTH]
        # assert any("auth.py" in a.path for a in auth_areas)

    def test_untested_module_is_flagged(self, sample_repo: Path):
        """app/utils.py has no test file — should be flagged as no-tests risk."""
        # TODO: Once implemented, assert:
        # areas = analyzer.analyze()
        # no_test_areas = [a for a in areas if a.category == RiskCategory.NO_TESTS]
        # assert any("utils.py" in a.path for a in no_test_areas)
        pass

    def test_tested_module_is_not_flagged_for_no_tests(self, sample_repo: Path):
        """app/main.py has tests/test_main.py — should NOT be flagged for no-tests."""
        # TODO: Once implemented, verify main.py does not appear in no-tests results
        pass


# ---------------------------------------------------------------------------
# OnboardingAgent integration tests
# ---------------------------------------------------------------------------


class TestOnboardingAgent:
    def test_agent_raises_not_implemented(self, sample_repo: Path):
        """
        The agent stub should raise NotImplementedError until implemented.
        This test will be updated to assert correct behavior once implemented.
        """
        agent = OnboardingAgent(repo_path=sample_repo)
        with pytest.raises(NotImplementedError):
            agent.analyze_repo()

    def test_agent_rejects_nonexistent_path(self):
        """Agent should raise an error if the repo path doesn't exist."""
        agent = OnboardingAgent(repo_path=Path("/nonexistent/path/xyz"))
        with pytest.raises((NotImplementedError, FileNotFoundError, ValueError)):
            agent.analyze_repo()

    def test_analyze_repo_convenience_function(self, sample_repo: Path):
        """The module-level analyze_repo() function should delegate to OnboardingAgent."""
        with pytest.raises(NotImplementedError):
            analyze_repo(sample_repo)
