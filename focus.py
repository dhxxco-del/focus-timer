#!/usr/bin/env python3
"""
Focus Timer — a simple Pomodoro timer with desktop notifications and session logging.

Usage:
  python3 focus.py                  # 25 min focus, 5 min break (default)
  python3 focus.py --focus 45       # custom focus length in minutes
  python3 focus.py --break 10       # custom break length in minutes
  python3 focus.py --log            # show today's session log
  python3 focus.py --stats          # show all-time stats
"""

import argparse
import csv
import datetime
import os
import subprocess
import sys
import time

LOG_FILE = os.path.join(os.path.dirname(__file__), "sessions.csv")
LOG_FIELDS = ["date", "start", "end", "type", "duration_min", "completed"]

# ─── Notifications ─────────────────────────────────────────────────────────────

def notify(title: str, message: str) -> None:
    script = f'display notification "{message}" with title "{title}" sound name "Glass"'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
    except Exception:
        pass  # notifications are best-effort


# ─── Logging ───────────────────────────────────────────────────────────────────

def log_session(start: datetime.datetime, end: datetime.datetime, kind: str, completed: bool) -> None:
    duration = round((end - start).total_seconds() / 60, 1)
    row = {
        "date": start.strftime("%Y-%m-%d"),
        "start": start.strftime("%H:%M:%S"),
        "end": end.strftime("%H:%M:%S"),
        "type": kind,
        "duration_min": duration,
        "completed": "yes" if completed else "no",
    }
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def read_log() -> list[dict]:
    if not os.path.isfile(LOG_FILE):
        return []
    with open(LOG_FILE, newline="") as f:
        return list(csv.DictReader(f))


# ─── Display helpers ───────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
DIM    = "\033[2m"

def bar(elapsed: int, total: int, width: int = 30) -> str:
    filled = int(width * elapsed / total)
    return f"[{GREEN}{'█' * filled}{DIM}{'░' * (width - filled)}{RESET}]"


def fmt_time(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


# ─── Timer ─────────────────────────────────────────────────────────────────────

def run_timer(label: str, minutes: int, color: str) -> bool:
    """Run a countdown timer. Returns True if completed, False if interrupted."""
    total = minutes * 60
    start = datetime.datetime.now()

    print(f"\n  {BOLD}{color}{label}{RESET}\n")
    try:
        for elapsed in range(total + 1):
            remaining = total - elapsed
            progress = bar(elapsed, total)
            line = f"  {progress}  {BOLD}{fmt_time(remaining)}{RESET} remaining"
            print(f"\r{line}", end="", flush=True)
            if elapsed < total:
                time.sleep(1)
        print()  # newline after bar
        return True
    except KeyboardInterrupt:
        end = datetime.datetime.now()
        print(f"\n\n  {YELLOW}Session interrupted.{RESET}")
        log_session(start, end, label.lower().replace(" ", "_"), completed=False)
        return False


# ─── Stats views ───────────────────────────────────────────────────────────────

def show_today() -> None:
    today = datetime.date.today().isoformat()
    rows = [r for r in read_log() if r["date"] == today and r["type"] == "focus" and r["completed"] == "yes"]
    if not rows:
        print(f"\n  {DIM}No completed focus sessions today.{RESET}\n")
        return
    total_min = sum(float(r["duration_min"]) for r in rows)
    print(f"\n  {BOLD}Today — {today}{RESET}")
    for r in rows:
        print(f"  {GREEN}✓{RESET}  {r['start']} → {r['end']}  ({r['duration_min']} min)")
    print(f"\n  {BOLD}{len(rows)} session{'s' if len(rows) != 1 else ''}  ·  {total_min:.0f} min total focus{RESET}\n")


def show_stats() -> None:
    rows = read_log()
    if not rows:
        print(f"\n  {DIM}No sessions logged yet.{RESET}\n")
        return
    focus_rows = [r for r in rows if r["type"] == "focus" and r["completed"] == "yes"]
    if not focus_rows:
        print(f"\n  {DIM}No completed focus sessions logged.{RESET}\n")
        return

    total_sessions = len(focus_rows)
    total_min = sum(float(r["duration_min"]) for r in focus_rows)
    days = len({r["date"] for r in focus_rows})
    avg = total_min / days if days else 0

    # Last 7 days
    today = datetime.date.today()
    print(f"\n  {BOLD}All-time stats{RESET}")
    print(f"  Sessions completed : {CYAN}{total_sessions}{RESET}")
    print(f"  Total focus time   : {CYAN}{total_min:.0f} min  ({total_min/60:.1f} hrs){RESET}")
    print(f"  Days with sessions : {CYAN}{days}{RESET}")
    print(f"  Avg per active day : {CYAN}{avg:.0f} min{RESET}")

    print(f"\n  {BOLD}Last 7 days{RESET}")
    for i in range(6, -1, -1):
        d = (today - datetime.timedelta(days=i)).isoformat()
        day_rows = [r for r in focus_rows if r["date"] == d]
        day_min = sum(float(r["duration_min"]) for r in day_rows)
        blocks = int(day_min / 25)
        bar_str = f"{GREEN}{'█' * blocks}{RESET}" if blocks else f"{DIM}·{RESET}"
        label = "today" if i == 0 else d
        print(f"  {label:<12}  {bar_str}  {day_min:.0f} min  ({len(day_rows)} sessions)")
    print()


# ─── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Focus Timer — Pomodoro with session logging")
    parser.add_argument("--focus",  type=int, default=25, metavar="MIN", help="Focus duration in minutes (default: 25)")
    parser.add_argument("--break",  type=int, default=5,  metavar="MIN", help="Break duration in minutes (default: 5)",  dest="brk")
    parser.add_argument("--log",    action="store_true", help="Show today's completed sessions")
    parser.add_argument("--stats",  action="store_true", help="Show all-time stats")
    args = parser.parse_args()

    if args.log:
        show_today()
        return

    if args.stats:
        show_stats()
        return

    print(f"\n  {BOLD}Focus Timer{RESET}  {DIM}(Ctrl+C to stop){RESET}")
    print(f"  Focus: {CYAN}{args.focus} min{RESET}  ·  Break: {CYAN}{args.brk} min{RESET}")

    session = 1
    while True:
        print(f"\n  {DIM}── Session {session} ──────────────────────────{RESET}")
        start = datetime.datetime.now()
        completed = run_timer("Focus", args.focus, CYAN)
        end = datetime.datetime.now()

        if not completed:
            sys.exit(0)

        log_session(start, end, "focus", completed=True)
        notify("Focus session complete!", f"Great work — {args.focus} min done. Time for a break.")
        print(f"\n  {GREEN}{BOLD}Session complete!{RESET}  Nice work.")

        start_brk = datetime.datetime.now()
        brk_completed = run_timer("Break", args.brk, YELLOW)
        end_brk = datetime.datetime.now()
        log_session(start_brk, end_brk, "break", completed=brk_completed)

        if not brk_completed:
            sys.exit(0)

        notify("Break over!", "Ready for another focus session?")
        print(f"\n  {YELLOW}{BOLD}Break done.{RESET}  Starting next session in 3 seconds…")
        time.sleep(3)
        session += 1


if __name__ == "__main__":
    main()
