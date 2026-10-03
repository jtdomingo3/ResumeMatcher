"""
Administrative & Security CLI for ResumeMatcher.
Provides safe zero-echo secret entry, validation, and key inspection.
Usage:
    python -m backend.app.cli secrets set-openrouter-key
    python -m backend.app.cli secrets verify
    python -m backend.app.cli secrets status
    python -m backend.app.cli secrets clear
"""

import argparse
import getpass
import sys
import httpx
from rich.console import Console
from rich.table import Table

from backend.app.core.secrets import SecretManager

console = Console()


def set_key():
    console.print("\n[bold cyan]Secure OpenRouter API Key Setup[/bold cyan]")
    console.print("This key will be stored securely in your OS Keyring (Windows Credential Manager / DPAPI).")
    console.print("[yellow]Input will be hidden to prevent shoulder-surfing and terminal history leaks.[/yellow]\n")

    try:
        raw_key = getpass.getpass("Enter OpenRouter API Key (sk-or-v1-...): ").strip()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[red]Cancelled by user.[/red]")
        sys.exit(1)

    if not raw_key:
        console.print("[red]Error: Key cannot be empty.[/red]")
        sys.exit(1)

    if not raw_key.startswith("sk-or-"):
        console.print("[red]Error: Invalid format. OpenRouter keys start with 'sk-or-'.[/red]")
        sys.exit(1)

    try:
        SecretManager.set_openrouter_key(raw_key)
        status = SecretManager.get_key_status()
        console.print(f"[bold green]✔ Successfully stored OpenRouter key in {status['source']}![/bold green]")
        console.print(f"Masked key: [bold]{status['masked']}[/bold]")
        console.print("Run [cyan]python -m backend.app.cli secrets verify[/cyan] to test connectivity.\n")
    except Exception as e:
        console.print(f"[bold red]Failed to save key:[/bold red] {e}")
        sys.exit(1)


def verify_key():
    console.print("\n[bold cyan]Verifying OpenRouter API Key...[/bold cyan]")
    status = SecretManager.get_key_status()

    if not status["has_key"]:
        console.print("[red]✘ No OpenRouter key found in OS Keyring or Environment.[/red]")
        console.print("Run [cyan]python -m backend.app.cli secrets set-openrouter-key[/cyan] to set one.")
        sys.exit(1)

    secret = SecretManager.get_openrouter_key()
    if not secret:
        console.print("[red]✘ Failed to resolve key.[/red]")
        sys.exit(1)

    raw = secret.get_secret_value()

    console.print(f"Source: [green]{status['source']}[/green]")
    console.print(f"Masked Key: [bold]{status['masked']}[/bold]")
    console.print("Pinging OpenRouter [cyan]https://openrouter.ai/api/v1/key[/cyan]...")

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://openrouter.ai/api/v1/key",
                headers={
                    "Authorization": f"Bearer {raw}",
                    "HTTP-Referer": "https://resume-matcher.local",
                    "X-Title": "AI Resume Matcher & Career Analyzer",
                },
            )

        if resp.status_code == 200:
            data = resp.json().get("data", {})
            table = Table(title="OpenRouter Key Verification Details")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            label = data.get("label", "Default")
            limit = data.get("limit")
            usage = data.get("usage", 0)
            rate_limit = data.get("rate_limit", {})

            table.add_row("Key Label", str(label))
            table.add_row("Usage", f"${usage:.4f}" if isinstance(usage, (int, float)) else str(usage))
            table.add_row("Credit Limit", f"${limit}" if limit is not None else "Unlimited")
            table.add_row("Rate Limit Requests", str(rate_limit.get("requests", "Standard")))
            table.add_row("Rate Limit Interval", str(rate_limit.get("interval", "10s")))
            table.add_row("Status", "ACTIVE & VALID")

            console.print(table)
            console.print("\n[bold green]✔ Connection to OpenRouter succeeded![/bold green]\n")
        else:
            console.print(f"[bold red]✘ OpenRouter returned HTTP {resp.status_code}:[/bold red] {resp.text}")
            sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]✘ Connection error:[/bold red] {e}")
        sys.exit(1)


def status_key():
    status = SecretManager.get_key_status()
    table = Table(title="Credential Security Status")
    table.add_column("Item", style="cyan")
    table.add_column("Status", style="yellow")

    table.add_row("Key Configured", "YES" if status["has_key"] else "NO")
    table.add_row("Resolution Source", status["source"])
    table.add_row("Masked Value", status["masked"] if status["masked"] else "(None)")
    table.add_row("Storage Security", "OS Protected Credential Manager" if status["source"] == "os_keyring" else "Environment")

    console.print(table)


def clear_key():
    confirm = input("Are you sure you want to remove the stored OpenRouter key from OS Keyring? (y/N): ")
    if confirm.lower() == "y":
        SecretManager.clear_openrouter_key()
        console.print("[green]✔ Stored key removed from Keyring.[/green]")
    else:
        console.print("Aborted.")


def main():
    parser = argparse.ArgumentParser(description="ResumeMatcher Security & Secret Management CLI")
    subparsers = parser.add_subparsers(dest="command")

    secrets_parser = subparsers.add_parser("secrets", help="Manage API credentials")
    secrets_sub = secrets_parser.add_subparsers(dest="action")

    secrets_sub.add_parser("set-openrouter-key", help="Safely enter and store OpenRouter API key")
    secrets_sub.add_parser("verify", help="Verify key connectivity and query OpenRouter quota")
    secrets_sub.add_parser("status", help="Display current masked credential status")
    secrets_sub.add_parser("clear", help="Remove stored key from OS Keyring")

    args = parser.parse_args()

    if args.command == "secrets":
        if args.action == "set-openrouter-key":
            set_key()
        elif args.action == "verify":
            verify_key()
        elif args.action == "status":
            status_key()
        elif args.action == "clear":
            clear_key()
        else:
            secrets_parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
