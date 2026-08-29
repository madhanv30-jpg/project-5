import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agent import run_agent, init
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()


def print_banner():
    banner = Text()
    banner.append("MADHAN'S PERSONAL SUPPORT AGENT", style="bold cyan")
    banner.append("  (Week 6)", style="dim yellow")
    console.print(Panel(banner, box=box.DOUBLE, border_style="magenta",
                        subtitle="[bold green]hybrid</bold> search · memory · guardrails ",
                        subtitle_align="center"))
    console.rule(style="blue")


def main():
    print_banner()

    console.print("Initializing knowledge base (Pinecone + BM25)...", style="cyan")
    count = init()
    console.print(f"Loaded [bold green]{count}[/bold green] document chunks.\n")

    session_id = str(uuid.uuid4())[:8]
    console.print(f"Session: [bold yellow]{session_id}[/bold yellow]")
    console.print("[dim]Commands: /remind <msg> | /history | /reminders | quit[/dim]\n")

    while True:
        try:
            user_input = input("madhan> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            console.print("Goodbye, Madhan.", style="bold cyan")
            break

        if user_input.lower() == "/history":
            from src.logger import read_session_log
            table = Table(title="Session Log", box=box.ROUNDED, border_style="blue")
            table.add_column("Kind", style="cyan")
            table.add_column("Content", style="white")
            for entry in read_session_log(session_id):
                kind = entry.get("kind", entry["role"])
                table.add_row(kind, entry["content"][:200])
            console.print(table)
            continue

        if user_input.lower() == "/reminders":
            from src.reminders import get_pending_reminders
            pending = get_pending_reminders()
            if not pending:
                console.print("No pending reminders.", style="yellow")
                continue
            table = Table(title="Reminders", box=box.ROUNDED, border_style="green")
            table.add_column("#", style="bold")
            table.add_column("Priority", style="cyan")
            table.add_column("Message", style="white")
            for r in pending:
                pri = r.get("priority", "normal")
                style = "red" if pri == "high" else "green"
                table.add_row(str(r["id"]), f"[{style}]{pri}[/{style}]", r["message"])
            console.print(table)
            continue

        if user_input.startswith("/remind "):
            from src.reminders import add_reminder
            r = add_reminder(user_input[8:])
            console.print(f"Reminder set: [bold green]#{r['id']}[/bold green] - {r['message']}", style="bright_cyan")
            continue

        out = run_agent(session_id=session_id, user_input=user_input)

        answer = Text(out["answer"])
        if out.get("escalated"):
            console.print(Panel(answer, border_style="red", title="[bold red]ESCALATED[/bold red]",
                                box=box.ROUNDED))
        else:
            console.print(Panel(answer, border_style="green", title="[bold green]Agent[/bold green]",
                                box=box.ROUNDED))

        if out.get("sources"):
            console.print("  [dim]sources:[/dim] " + ", ".join(
                f"[cyan]{s}[/cyan]" for s in out["sources"]))
        if out.get("escalated"):
            console.print("[bold red][!][/bold red] Escalated to Madhan.")
        if out.get("needs_human"):
            console.print("[bold yellow][!][/bold yellow] Flagged for Madhan's attention.")


if __name__ == "__main__":
    main()
