#!/usr/bin/env python3
"""
run_onboarding.py — example script for repo-onboarding-agent

Demonstrates how to invoke the OnboardingAgent, render the report to Markdown,
and save it to a file.

Usage:
    python examples/run_onboarding.py --repo /path/to/some/project
    python examples/run_onboarding.py --repo . --output reports/my-project.md
    python examples/run_onboarding.py --repo . --json           # also save JSON
    python examples/run_onboarding.py --repo . --verbose        # verbose output
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Rich is used for console output; fall back to plain print if not installed
# ---------------------------------------------------------------------------
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table

    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

    class _FallbackConsole:
        def print(self, *args, **kwargs):
            print(*args)
        def rule(self, *args, **kwargs):
            print("-" * 60)

    console = _FallbackConsole()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a structured onboarding brief for a code repository.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python examples/run_onboarding.py --repo .
  python examples/run_onboarding.py --repo ~/src/my-api --verbose
  python examples/run_onboarding.py --repo /path/to/repo --output reports/brief.md
        """,
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        metavar="PATH",
        help="Path to the repository root to analyze (default: current directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="FILE",
        help="Output file path for the Markdown report (default: reports/<repo-name>-onboarding.md)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also save the report as JSON alongside the Markdown",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output during analysis",
    )
    return parser.parse_args()


def resolve_output_path(repo_path: Path, output_arg: Path | None) -> Path:
    """Determine the output file path for the Markdown report."""
    if output_arg is not None:
        return output_arg.resolve()
    repo_name = repo_path.resolve().name
    output_dir = Path(__file__).parent.parent / "reports"
    output_dir.mkdir(exist_ok=True)
    return output_dir / f"{repo_name}-onboarding.md"


def print_summary_table(report) -> None:
    """Print a summary of the report to the console."""
    if HAS_RICH:
        table = Table(title=f"Onboarding Report: {report.repo_name}", show_header=False, padding=(0, 1))
        table.add_column("Field", style="bold cyan")
        table.add_column("Value")
        table.add_row("Language", report.primary_language)
        table.add_row("Files", str(report.file_count))
        table.add_row("Lines", f"{report.line_count:,}")
        table.add_row("Commands found", str(len(report.commands)))
        table.add_row("Entry points", str(len(report.entry_points)))
        table.add_row("Risky areas", str(len(report.risky_areas)))
        table.add_row("First-good tasks", str(len(report.first_good_tasks)))
        table.add_row("Open questions", str(len(report.open_questions)))
        console.print(table)
    else:
        console.print(report.summary())


def run_analysis(repo_path: Path, verbose: bool):
    """
    Run the onboarding agent on the given repo path.

    This is a placeholder that simulates the multi-stage analysis pipeline.
    Replace the NotImplementedError handling with actual agent invocation
    once the analyzers are implemented.
    """
    # Import here so the script gives a clear error if the package isn't installed
    try:
        from src.agent import OnboardingAgent
    except ImportError:
        console.print(
            "[red]Error:[/red] Could not import src.agent. "
            "Run this script from the repo-onboarding-agent root directory.",
            style="red" if HAS_RICH else None,
        )
        sys.exit(1)

    stages = [
        "Scanning directory structure",
        "Inferring tech stack",
        "Extracting commands",
        "Mapping entry points",
        "Detecting risky areas",
        "Suggesting first good tasks",
    ]

    agent = OnboardingAgent(repo_path=repo_path, verbose=verbose)

    if HAS_RICH:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=False,
        ) as progress:
            for i, stage in enumerate(stages, 1):
                task = progress.add_task(f"[{i}/{len(stages)}] {stage}...", total=None)
                # Simulate work — replace with real agent calls
                time.sleep(0.1)
                progress.update(task, description=f"[{i}/{len(stages)}] {stage}... ✓", completed=1, total=1)
    else:
        for i, stage in enumerate(stages, 1):
            print(f"[{i}/{len(stages)}] {stage}...")

    try:
        report = agent.analyze_repo()
    except NotImplementedError:
        console.print(
            "\n[yellow]Note:[/yellow] The analyzer is not yet implemented — "
            "returning a stub report for demonstration.\n"
            if HAS_RICH
            else "\nNote: The analyzer is not yet implemented — returning a stub report.\n"
        )
        # Return a minimal stub report for demonstration purposes
        from src.agent import OnboardingReport
        report = OnboardingReport(
            repo_name=repo_path.resolve().name,
            repo_path=str(repo_path.resolve()),
            project_overview=(
                "Analysis not yet available — analyzers are not implemented. "
                "See src/analyzers/ for implementation stubs."
            ),
            primary_language="unknown",
        )

    return agent, report


def main() -> None:
    args = parse_args()
    repo_path = args.repo.resolve()

    if not repo_path.exists():
        console.print(f"Error: repository path does not exist: {repo_path}")
        sys.exit(1)

    if not repo_path.is_dir():
        console.print(f"Error: repository path is not a directory: {repo_path}")
        sys.exit(1)

    console.rule(f"repo-onboarding-agent: {repo_path.name}" if HAS_RICH else "")
    console.print()

    start = time.monotonic()
    agent, report = run_analysis(repo_path, verbose=args.verbose)
    elapsed = time.monotonic() - start

    console.print()
    print_summary_table(report)
    console.print()

    # Determine output paths
    output_md = resolve_output_path(repo_path, args.output)
    formats = ["markdown"]
    if args.json:
        formats.append("json")

    # Save (stub — would call agent.save_report() once implemented)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    try:
        md_content = agent.render_markdown(report)
    except NotImplementedError:
        md_content = f"# Onboarding Report: {report.repo_name}\n\n*(Renderer not yet implemented)*\n"

    output_md.write_text(md_content, encoding="utf-8")
    console.print(f"Report written to: {output_md}")

    if args.json:
        output_json = output_md.with_suffix(".json")
        output_json.write_text(report.to_json(), encoding="utf-8")
        console.print(f"JSON written to:   {output_json}")

    console.print(f"\nCompleted in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
