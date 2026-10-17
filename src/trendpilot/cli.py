"""Command line for the agent. The UI lives elsewhere."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trendpilot.agent import run
from trendpilot.profiles import PROFILES


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _utf8_stdio()
    parser = argparse.ArgumentParser(prog="trendpilot", description="Run the TrendPilot research agent.")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Research one company and print findings JSON")
    run_parser.add_argument("company", nargs="?", help="Path to a company JSON file. Omit to use the demo yard.")
    run_parser.add_argument("--question", default="", help="Optional owner question")
    run_parser.add_argument("--profile", default="", help="Built-in demo profile name")
    run_parser.add_argument("--out", default="", help="Also write findings JSON to this file")

    sub.add_parser("profiles", help="Print built-in demo profiles")
    sub.add_parser("serve", help="Local JSON API for a separate UI")
    sub.add_parser("desktop", help="Start TrendPilot in the background and open its UI")

    args = parser.parse_args(argv)
    if args.command == "profiles":
        json.dump(PROFILES, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    if args.command == "serve":
        from trendpilot.serve import serve

        serve()
        return 0
    if args.command == "desktop":
        from trendpilot.desktop import launch

        return launch()
    return _run(args)


def _run(args: argparse.Namespace) -> int:
    if args.profile:
        try:
            company = PROFILES[args.profile]
        except KeyError:
            print("Unknown profile. Use: trendpilot profiles", file=sys.stderr)
            return 2
    elif args.company:
        company = json.loads(Path(args.company).read_text(encoding="utf-8"))
    else:
        company = PROFILES["Yard — Karatau Materials"]

    findings = None
    for event in run(company, question=args.question.strip() or None):
        if event["kind"] == "done":
            findings = (event.get("payload") or {}).get("findings")
            continue
        detail = (event.get("detail") or "").replace("\n", " | ")
        print(f"[{event['kind']}] {event['title']}: {detail[:240]}", file=sys.stderr, flush=True)

    text = json.dumps(findings, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.write(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0 if findings else 1
