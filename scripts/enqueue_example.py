"""
scripts/enqueue_example.py
───────────────────────────
Demo script — enqueues a batch of example LLM outputs to test the pipeline.

Run with:
    python scripts/enqueue_example.py

LESSON — This script shows the producer side of the system.
In a real application, you'd call HITLClient.enqueue() right after
receiving a response from an LLM API.
"""

import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

from hitl_eval_client import HITLClient

console = Console()

EXAMPLES = [
    {
        "prompt_id": "summariser_v1",
        "prompt": "Summarise the following in 2 sentences:\n\nMachine learning models require large amounts of labelled training data. The process of collecting and labelling this data is expensive and time-consuming, often requiring domain experts. Active learning attempts to reduce this cost by intelligently selecting the most informative samples for labelling.",
        "output": "Machine learning models need large labeled datasets, which are costly to create. Active learning reduces this burden by strategically selecting the most valuable samples to label.",
        "model": "gpt-4o",
    },
    {
        "prompt_id": "summariser_v1",
        "prompt": "Summarise the following in 2 sentences:\n\nThe human gut contains trillions of microorganisms collectively known as the microbiome. These bacteria, fungi, and viruses play a crucial role in digestion, immune function, and even mental health through the gut-brain axis.",
        "output": "The gut microbiome consists of trillions of microorganisms including bacteria, fungi, and viruses. They influence digestion, immunity, and mental wellbeing via the gut-brain connection. Additionally, research suggests that diet significantly impacts microbiome composition.",
        "model": "gpt-4o",
        # Note: This output has 3 sentences, not 2 — intentionally "bad" for labeling demo
    },
    {
        "prompt_id": "summariser_v1",
        "prompt": "Summarise the following in 2 sentences:\n\nQuantum computing harnesses the principles of quantum mechanics to process information. Unlike classical bits that are either 0 or 1, quantum bits (qubits) can exist in superposition — being both 0 and 1 simultaneously — enabling exponentially faster computation for certain problems.",
        "output": "Quantum computers use quantum mechanics, allowing qubits to exist in superposition as both 0 and 1 simultaneously. This enables exponentially faster computation for specific problem types compared to classical computers.",
        "model": "claude-3-5-sonnet",
    },
    {
        "prompt_id": "codegen_v1",
        "prompt": "Write a Python function to check if a string is a palindrome.",
        "output": "def is_palindrome(s: str) -> bool:\n    cleaned = s.lower().replace(' ', '')\n    return cleaned == cleaned[::-1]",
        "model": "gpt-4o",
    },
    {
        "prompt_id": "codegen_v1",
        "prompt": "Write a Python function that returns the nth Fibonacci number.",
        "output": "def fibonacci(n):\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b",
        "model": "claude-3-5-sonnet",
    },
    {
        "prompt_id": "support_v1",
        "prompt": "Customer: 'I ordered the wrong size. Can I exchange it?'",
        "output": "I'm sorry to hear that! Yes, we offer free exchanges within 30 days of purchase. Please visit our returns portal at returns.example.com with your order number and select 'Exchange'. Your new item will ship within 2 business days of us receiving the return.",
        "model": "gpt-4o",
        "metadata": {"channel": "chat", "customer_tier": "standard"},
    },
]


def main():
    console.print("\n[bold]HITL Eval — Enqueue Demo[/bold]", style="cyan")
    console.print("Connecting to http://localhost:8000...\n")

    with HITLClient(base_url="http://localhost:8000") as client:
        # Health check
        if not client.health():
            console.print("[red]❌ Server not reachable. Is it running?[/red]")
            console.print("Start with: [cyan]uvicorn backend.main:app --reload[/cyan]")
            return

        console.print(f"[green]✅ Server healthy[/green]\n")
        console.print(f"Enqueueing [bold]{len(EXAMPLES)}[/bold] example items...\n")

        # Table to show results
        table = Table(title="Enqueued Items")
        table.add_column("Prompt ID", style="cyan")
        table.add_column("Model", style="dim")
        table.add_column("Item ID", style="dim")
        table.add_column("Queue Depth", justify="right")

        for ex in EXAMPLES:
            result = client.enqueue(
                prompt=ex["prompt"],
                output=ex["output"],
                prompt_id=ex["prompt_id"],
                model=ex.get("model"),
                metadata=ex.get("metadata"),
            )
            table.add_row(
                ex["prompt_id"],
                ex.get("model", "—"),
                result["item_id"][:12] + "...",
                str(result["queue_depth"]),
            )

        console.print(table)
        console.print(f"\n[green]✅ Done! Open http://localhost:8000 to start labeling.[/green]\n")


if __name__ == "__main__":
    main()
