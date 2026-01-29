"""
Eval Command - Run and compare model evaluations.
"""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(help="Run model evaluations")
console = Console()


@app.command(name="run")
def run_evals(
    model: str = typer.Option("gemini-2.0-flash", "--model", "-m", help="Model to evaluate"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Filter by tags (comma-separated)"),
    parallel: bool = typer.Option(False, "--parallel", help="Run tests in parallel"),
):
    """Run evaluation suite against a model."""
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.evals.runner import EvalRunner, load_test_cases

        console.print(f"\n[bold]Running evaluations with model: {model}[/bold]")

        # Load test cases
        test_cases = load_test_cases()
        original_count = len(test_cases)

        if category:
            test_cases = [tc for tc in test_cases if tc.category == category]

        if tags:
            tag_list = [t.strip() for t in tags.split(",")]
            test_cases = [tc for tc in test_cases if any(t in tc.tags for t in tag_list)]

        console.print(f"Found {len(test_cases)} test cases (filtered from {original_count})")

        if not test_cases:
            console.print("[yellow]No test cases match the filters.[/yellow]")
            return

        # Run evaluations
        runner = EvalRunner(model_id=model, parallel=parallel)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running evaluations...", total=None)
            summary = runner.run_suite(test_cases)
            progress.update(task, completed=True)

        # Display results
        table = Table(title=f"Evaluation Results: {model}")
        table.add_column("Test", style="cyan")
        table.add_column("Score")
        table.add_column("Status")
        table.add_column("Duration")

        for result in summary.test_results:
            status_color = "green" if result.passed else "red"
            status = "PASS" if result.passed else "FAIL"
            if result.error:
                status = "ERROR"
                status_color = "yellow"

            table.add_row(
                result.test_case_id,
                f"{result.overall_score:.2f}",
                f"[{status_color}]{status}[/{status_color}]",
                f"{result.duration_seconds:.1f}s",
            )

        console.print(table)

        # Summary
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Total: {summary.total_tests}")
        console.print(f"  Passed: [green]{summary.passed_tests}[/green]")
        console.print(f"  Failed: [red]{summary.failed_tests}[/red]")
        console.print(f"  Errors: [yellow]{summary.error_tests}[/yellow]")
        console.print(f"  Average Score: {summary.average_score:.1%}")

    except Exception as e:
        console.print(f"[red]Error running evals: {e}[/red]")


@app.command(name="compare")
def compare_models(
    model_a: str = typer.Option(..., "--model-a", "-a", help="First model"),
    model_b: str = typer.Option(..., "--model-b", "-b", help="Second model"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
):
    """Compare two models on the same test suite."""
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.evals.runner import compare_models as run_comparison

        console.print(f"\n[bold]Comparing models:[/bold] {model_a} vs {model_b}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running comparisons...", total=None)
            categories = [category] if category else None
            comparison = run_comparison(model_a, model_b, categories)
            progress.update(task, completed=True)

        # Results table
        table = Table(title="Model Comparison")
        table.add_column("Metric", style="cyan")
        table.add_column(model_a)
        table.add_column(model_b)

        table.add_row(
            "Average Score",
            f"{comparison.model_a_summary.average_score:.1%}",
            f"{comparison.model_b_summary.average_score:.1%}",
        )
        table.add_row(
            "Tests Passed",
            str(comparison.model_a_summary.passed_tests),
            str(comparison.model_b_summary.passed_tests),
        )
        table.add_row(
            "Tests Failed",
            str(comparison.model_a_summary.failed_tests),
            str(comparison.model_b_summary.failed_tests),
        )

        console.print(table)

        # Winner
        winner_color = "green"
        if comparison.winner == "tie":
            console.print(f"\n[yellow]Result: TIE (margin: {comparison.margin:.1%})[/yellow]")
        else:
            console.print(f"\n[{winner_color}]Winner: {comparison.winner} (margin: {comparison.margin:.1%})[/{winner_color}]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command(name="list")
def list_tests(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
):
    """List available test cases."""
    try:
        import sys
        sys.path.insert(0, str(__file__).rsplit('cli', 1)[0])
        from backend.app.evals import load_test_cases

        test_cases = load_test_cases()

        if category:
            test_cases = [tc for tc in test_cases if tc.category == category]

        if test_cases:
            table = Table(title=f"Test Cases ({len(test_cases)})")
            table.add_column("ID", style="cyan")
            table.add_column("Name")
            table.add_column("Agent")
            table.add_column("Category")

            for tc in test_cases:
                table.add_row(
                    tc.id,
                    tc.name,
                    tc.agent_role,
                    tc.category,
                )

            console.print(table)
        else:
            console.print("[yellow]No test cases found.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
