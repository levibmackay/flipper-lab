#!/usr/bin/env python3
"""
flipper_ctl — control your Flipper Zero over USB from SSH.

Usage:
  python3 flipper_ctl.py info
  python3 flipper_ctl.py list
  python3 flipper_ctl.py upload payloads/exfil_flag.txt
  python3 flipper_ctl.py run exfil_flag.txt
  python3 flipper_ctl.py delete exfil_flag.txt
"""

import sys
import time
import argparse
import os

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

BADUSB_DIR = "/ext/badusb"
SERIAL_PORT = "/dev/ttyACM0"

# How long to wait for the Bad USB app to open before sending button presses
APP_LOAD_DELAY = 1.5
BUTTON_DELAY   = 0.3


def connect(port=SERIAL_PORT):
    try:
        from pyflipper.pyflipper import PyFlipper
        f = PyFlipper(com=port)
        return f
    except Exception as e:
        console.print(f"[red]Cannot connect to Flipper on {port}:[/red] {e}")
        console.print("[dim]Is the Flipper plugged in? Check: ls /dev/ttyACM*[/dim]")
        sys.exit(1)


def cmd_info(args):
    f = connect(args.port)
    with console.status("[cyan]Reading device info…"):
        info = f.device_info.get()
    console.print()
    console.print(Panel(
        "\n".join(f"[dim]{k}:[/dim]  [white]{v}[/white]" for k, v in info.items()),
        title="[cyan]Flipper Zero[/cyan]",
        border_style="cyan",
        expand=False,
        padding=(0, 2),
    ))


def cmd_list(args):
    f = connect(args.port)
    with console.status(f"[cyan]Listing {BADUSB_DIR}…"):
        result = f.storage.list(path=BADUSB_DIR)

    files = result.get("files", [])
    dirs  = result.get("dirs", [])

    if not files and not dirs:
        console.print("[yellow]No payloads found on Flipper.[/yellow]")
        console.print(f"[dim]Upload one with: python3 flipper_ctl.py upload <file>[/dim]")
        return

    t = Table(box=box.ROUNDED, header_style="bold cyan")
    t.add_column("#",        width=4,  justify="right")
    t.add_column("Payload",  min_width=30)
    t.add_column("Size",     width=10, justify="right")

    for i, f_info in enumerate(files, 1):
        size = f"{f_info['size']} {f_info['weight']}"
        t.add_row(str(i), f_info["name"], f"[dim]{size}[/dim]")

    console.print()
    console.print(t)
    console.print(f"\n[dim]Run a payload:[/dim]  python3 flipper_ctl.py run <filename>")


def cmd_upload(args):
    local_path = args.file
    if not os.path.exists(local_path):
        console.print(f"[red]File not found:[/red] {local_path}")
        sys.exit(1)

    filename = os.path.basename(local_path)
    flipper_path = f"{BADUSB_DIR}/{filename}"

    with open(local_path, "r") as fh:
        content = fh.read()

    f = connect(args.port)

    # Ensure the badusb directory exists
    try:
        f.storage.mkdir(BADUSB_DIR)
    except Exception:
        pass  # already exists

    with console.status(f"[cyan]Uploading {filename} to Flipper…"):
        f.storage.write.file(text=content, path=flipper_path)

    console.print(f"[green]✓[/green] Uploaded [bold]{filename}[/bold] → [dim]{flipper_path}[/dim]")


def cmd_run(args):
    payload_name = args.payload
    if not payload_name.endswith(".txt"):
        payload_name += ".txt"

    flipper_path = f"{BADUSB_DIR}/{payload_name}"

    f = connect(args.port)

    # Verify the file exists on the Flipper
    with console.status("[cyan]Checking payload exists on Flipper…"):
        result = f.storage.list(path=BADUSB_DIR)
        names = [fi["name"] for fi in result.get("files", [])]

    if payload_name not in names:
        console.print(f"[red]Payload not found on Flipper:[/red] {payload_name}")
        console.print(f"[dim]Available: {', '.join(names) or 'none'}[/dim]")
        console.print(f"[dim]Upload it first: python3 flipper_ctl.py upload payloads/{payload_name}[/dim]")
        sys.exit(1)

    # Find index so we can navigate the Bad USB file picker
    names_sorted = sorted(names)
    try:
        index = names_sorted.index(payload_name)
    except ValueError:
        index = 0

    console.print(f"\n[bold cyan]Running:[/bold cyan] {payload_name}")
    console.print(f"[dim]Position in list: {index + 1} of {len(names_sorted)}[/dim]")
    console.print("[yellow]Make sure the Flipper is plugged into the Pi USB and the target terminal has focus.[/yellow]\n")

    # Open the Bad USB app
    with console.status("[cyan]Opening Bad USB app on Flipper…"):
        try:
            f.loader.open("Bad USB")
        except Exception as e:
            console.print(f"[red]Could not open Bad USB app:[/red] {e}")
            sys.exit(1)

    time.sleep(APP_LOAD_DELAY)

    # Navigate down to the right file
    if index > 0:
        with console.status(f"[cyan]Navigating to {payload_name}…"):
            for _ in range(index):
                f.input.send("down", "short")
                time.sleep(BUTTON_DELAY)

    time.sleep(0.3)

    # Press OK to select and run
    with console.status("[cyan]Pressing OK to run…"):
        f.input.send("ok", "short")
        time.sleep(BUTTON_DELAY)
        f.input.send("ok", "short")

    console.print(f"[green bold]✓ Payload sent![/green bold] Watch the terminal for output.")


def cmd_delete(args):
    payload_name = args.payload
    if not payload_name.endswith(".txt"):
        payload_name += ".txt"

    flipper_path = f"{BADUSB_DIR}/{payload_name}"
    f = connect(args.port)

    with console.status(f"[cyan]Deleting {payload_name}…"):
        f.storage.remove(file=flipper_path)

    console.print(f"[green]✓[/green] Deleted [bold]{payload_name}[/bold] from Flipper.")


def main():
    parser = argparse.ArgumentParser(
        description="Control Flipper Zero Bad USB over SSH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  info                    Show Flipper device info
  list                    List Bad USB payloads on the Flipper SD card
  upload <file>           Upload a local payload to the Flipper
  run    <payload>        Run a payload by name (navigates the Flipper UI remotely)
  delete <payload>        Delete a payload from the Flipper SD card

Examples:
  python3 flipper_ctl.py info
  python3 flipper_ctl.py upload payloads/exfil_flag.txt
  python3 flipper_ctl.py list
  python3 flipper_ctl.py run exfil_flag.txt
        """
    )
    parser.add_argument("--port", default=SERIAL_PORT, help=f"Serial port (default: {SERIAL_PORT})")

    sub = parser.add_subparsers(dest="command")
    sub.required = True

    sub.add_parser("info",  help="Show Flipper device info")
    sub.add_parser("list",  help="List Bad USB payloads on the Flipper")

    p_upload = sub.add_parser("upload", help="Upload a payload to the Flipper")
    p_upload.add_argument("file", help="Local .txt payload file to upload")

    p_run = sub.add_parser("run", help="Run a Bad USB payload remotely")
    p_run.add_argument("payload", help="Payload filename (e.g. exfil_flag.txt)")

    p_del = sub.add_parser("delete", help="Delete a payload from the Flipper")
    p_del.add_argument("payload", help="Payload filename to delete")

    args = parser.parse_args()

    dispatch = {
        "info":   cmd_info,
        "list":   cmd_list,
        "upload": cmd_upload,
        "run":    cmd_run,
        "delete": cmd_delete,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
