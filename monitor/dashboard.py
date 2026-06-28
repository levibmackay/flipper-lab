#!/usr/bin/env python3
"""Live terminal dashboard — watch attacks against the vulnerable server in real time."""

import os
import sys
import time
from collections import deque
from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

LOG_PATH = os.path.join(os.path.dirname(__file__), "../requests.log")

ATTACK_SIGNATURES = {
    "SQL Injection":       ["'", "OR 1=1", "--", "UNION SELECT", "DROP TABLE"],
    "Command Injection":   [";", "&&", "||", "`", "$(", "/bin/", "cat /etc"],
    "Directory Traversal": ["../", "..\\", "%2e%2e", "/etc/passwd", "/etc/shadow"],
    "IDOR Probe":          ["/api/user/1", "/api/user/3", "/api/user/4"],
}

STATS = {"total": 0, "attacks": 0, "logins": 0, "login_fails": 0}
RECENT: deque = deque(maxlen=20)
ATTACK_LOG: deque = deque(maxlen=10)


def detect_attack(line: str):
    line_up = line.upper()
    for attack_type, sigs in ATTACK_SIGNATURES.items():
        for sig in sigs:
            if sig.upper() in line_up:
                return attack_type
    return None


def classify_row(line: str):
    style = "dim"
    tag = ""
    attack = detect_attack(line)
    if attack:
        style = "bold red"
        tag = f"[red][{attack}][/red]"
        STATS["attacks"] += 1
        ATTACK_LOG.append((datetime.now().strftime("%H:%M:%S"), attack, line.strip()))
    elif "LOGIN SUCCESS" in line:
        style = "green"
        tag = "[green][AUTH OK][/green]"
        STATS["logins"] += 1
    elif "LOGIN FAILED" in line or "LOGIN ATTEMPT" in line:
        style = "yellow"
        tag = "[yellow][AUTH FAIL][/yellow]"
        STATS["login_fails"] += 1
    return style, tag


def build_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=5),
    )
    layout["body"].split_row(
        Layout(name="requests", ratio=3),
        Layout(name="attacks", ratio=2),
    )
    return layout


def render_header():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return Panel(
        f"[bold cyan]Flipper Lab — Live Attack Monitor[/bold cyan]  "
        f"[dim]{now}[/dim]  "
        f"Requests: [white]{STATS['total']}[/white]  "
        f"Attacks: [red]{STATS['attacks']}[/red]  "
        f"Auth OK: [green]{STATS['logins']}[/green]  "
        f"Auth Fail: [yellow]{STATS['login_fails']}[/yellow]",
        border_style="cyan",
    )


def render_requests():
    t = Table(box=box.SIMPLE, header_style="bold cyan", expand=True)
    t.add_column("Time",    width=8)
    t.add_column("IP",      width=15)
    t.add_column("Request", min_width=30)
    t.add_column("Tag",     width=22)

    for entry in RECENT:
        t.add_row(*entry)

    return Panel(t, title="[bold]Recent Requests[/bold]", border_style="blue")


def render_attacks():
    t = Table(box=box.SIMPLE, header_style="bold red", expand=True)
    t.add_column("Time",   width=8)
    t.add_column("Type",   width=20)
    t.add_column("Detail", min_width=20)

    for ts, atype, detail in ATTACK_LOG:
        short = detail[:40] + "…" if len(detail) > 40 else detail
        t.add_row(ts, f"[red]{atype}[/red]", f"[dim]{short}[/dim]")

    return Panel(t, title="[bold red]Detected Attacks[/bold red]", border_style="red")


def render_footer():
    tips = (
        "[dim]Attacks to try:[/dim]  "
        "[yellow]SQL:[/yellow] username: [cyan]' OR '1'='1[/cyan]  "
        "[yellow]CMD:[/yellow] ping host: [cyan]127.0.0.1; id[/cyan]  "
        "[yellow]TRAV:[/yellow] file: [cyan]../flag.txt[/cyan]  "
        "[yellow]IDOR:[/yellow] [cyan]/api/user/1[/cyan]  "
        "[yellow]Admin:[/yellow] [cyan]admin / password123[/cyan]"
    )
    return Panel(tips, border_style="dim")


def tail_log(path: str):
    """Open log file and seek to end, then yield new lines as they arrive."""
    while not os.path.exists(path):
        time.sleep(0.5)
    with open(path) as f:
        f.seek(0, 2)
        while True:
            line = f.readline()
            if line:
                yield line
            else:
                time.sleep(0.2)


def main():
    console = Console()
    layout = build_layout()
    tailer = tail_log(LOG_PATH)

    console.print(f"[cyan]Watching[/cyan] {LOG_PATH}  (Ctrl+C to quit)\n")

    with Live(layout, console=console, refresh_per_second=4, screen=True):
        for line in tailer:
            STATS["total"] += 1
            style, tag = classify_row(line)

            parts = line.strip().split("|")
            ts  = parts[0].strip()[-8:] if parts else ""
            ip  = parts[1].strip() if len(parts) > 1 else ""
            req = parts[2].strip() if len(parts) > 2 else line.strip()

            RECENT.appendleft((
                Text(ts,  style="dim"),
                Text(ip,  style="cyan"),
                Text(req[:60], style=style),
                Text.from_markup(tag),
            ))

            layout["header"].update(render_header())
            layout["requests"].update(render_requests())
            layout["attacks"].update(render_attacks())
            layout["footer"].update(render_footer())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
