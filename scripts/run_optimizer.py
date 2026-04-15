"""
scripts/run_optimizer.py
─────────────────────────
CLI script to trigger the DSPy prompt optimizer.

Run with:
    python scripts/run_optimizer.py --prompt-id summariser_v1 --base-prompt "Summarise in 2 sentences:"

LESSON — CLI tools with Typer:
Typer wraps Python functions as CLI commands, deriving argument names and
types from function signatures and type annotations. It's much less boilerplate
than argparse and produces rich --help output automatically.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from backend.core.config import settings
from backend.db.session import get_session, init_db
from backend.optimizer.dspy_optimizer import HITLOptimizer

app = typer.Typer(help="Run the DSPy prompt optimizer")
console = Console()


@app.command()
def optimize(
    prompt_id: str = typer.Option(..., help="Prompt ID to optimize (e.g. 'summariser_v1')"),
    base_prompt: str = typer.Option(..., help="Current prompt text to improve"),
    min_labels: int = typer.Option(10, help="Minimum labels required before optimizing"),
):
    """
    Run the DSPy optimization loop for a given prompt ID.

    Reads good labels from the database, selects few-shot examples,
    and rewrites your prompt with them baked in.
    """
    asyncio.run(_run(prompt_id, base_prompt, min_labels))


async def _run(prompt_id: str, base_prompt: str, min_labels: int):
    console.print(f"\n[bold cyan]HITL Eval — Prompt Optimizer[/bold cyan]")
    console.print(f"Prompt ID : [yellow]{prompt_id}[/yellow]")
    console.print(f"Min labels: [yellow]{min_labels}[/yellow]\n")

    # Initialise DB
    await init_db()

    async with get_session() as session:
        optimizer = HITLOptimizer(session)
        result = await optimizer.run(
            prompt_id=prompt_id,
            base_prompt=base_prompt,
            min_labels=min_labels,
        )

    if not result.success:
        console.print(f"[red]❌ Optimization failed:[/red] {result.error}")
        raise typer.Exit(1)

    console.print(f"[green]✅ Optimization complete![/green]")
    console.print(f"  Good labels  : {result.good_count}")
    console.print(f"  Bad labels   : {result.bad_count}")
    console.print(f"  Examples used: {result.examples_used}")
    console.print(f"  Duration     : {result.duration_ms:.1f}ms")
    console.print(f"  Optimizer    : {result.optimizer_used}\n")

    console.print(Panel(
        Syntax(result.optimized_prompt, "text", theme="monokai", word_wrap=True),
        title="[bold green]Optimized Prompt[/bold green]",
        border_style="green",
    ))

    # Save to file for convenience
    out_path = Path(f"optimized_{prompt_id}.txt")
    out_path.write_text(result.optimized_prompt)
    console.print(f"\n[dim]Saved to {out_path}[/dim]")


if __name__ == "__main__":
    app()
