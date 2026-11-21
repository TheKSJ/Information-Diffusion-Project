import argparse
import json
import logging
from pathlib import Path

from .storage import load_config


def main(argv=None):
    parser = argparse.ArgumentParser(description="Auditable filing-timed event study; no trading or causal claims")
    subs = parser.add_subparsers(dest="command", required=True)
    for name, help_text in [("validate", "Validate the fixed design and 30-security universe"),
                            ("fetch", "Collect SEC filings and explicit adjusted prices; resume from cache"),
                            ("run", "Analyze cached inputs; never creates synthetic replacements"),
                            ("report", "Render technical tables and figures from analytical outputs")]:
        sub = subs.add_parser(name, help=help_text)
        sub.add_argument("--config", default="configs/study.yaml")
        if name == "fetch":
            sub.add_argument("--pilot", action="store_true", help="Preflight AAPL/JPM/CAT only")
            sub.add_argument("--offline", action="store_true", help="Cache only; network prohibited")
            sub.add_argument("--prices-only", action="store_true")
    demo = subs.add_parser("demo", help="Fully offline SYNTHETIC end-to-end integration demonstration")
    demo.add_argument("--offline", action="store_true", required=True)
    demo.add_argument("--output", default="reports/demo")
    desk = subs.add_parser("serve", help="Open the local interactive research desk")
    desk.add_argument("--config", default="configs/study.yaml")
    desk.add_argument("--port", type=int, default=8765)
    desk.add_argument("--no-browser", action="store_true", help="Serve without opening a browser automatically")
    launcher = subs.add_parser("open-desk", help="Start or reopen the persistent local research desk")
    launcher.add_argument("--config", default="configs/study.yaml")
    launcher.add_argument("--port", type=int, default=8765)
    launcher.add_argument("--no-browser", action="store_true")
    closer = subs.add_parser("close-desk", help="Close the local desk after its current task finishes")
    closer.add_argument("--config", default="configs/study.yaml")
    closer.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    try:
        if args.command == "demo":
            from .demo import run_demo
            result = run_demo(Path(args.output))
        else:
            config = load_config(args.config)
            if args.command == "serve":
                from .desk import serve
                result = serve(config, args.port, not args.no_browser)
            elif args.command == "open-desk":
                from .desk import open_desk
                result = open_desk(config, args.port, not args.no_browser)
            elif args.command == "close-desk":
                from .desk import close_desk
                result = close_desk(config, args.port)
            elif args.command == "validate":
                from .validation import validate_config
                universe = validate_config(config)
                result = {"status": "valid", "fixed_universe": len(universe), "estimation_observations": 100}
            elif args.command == "fetch":
                from .collection import fetch
                result = fetch(config, args.pilot, args.offline, args.prices_only)
                print(json.dumps({k: v for k, v in result.items() if k != "snapshots"}, indent=2))
                return 2 if result["failed_operations"] else 0
            elif args.command == "run":
                from .pipeline import run
                result = run(config)
                print(json.dumps(result, indent=2))
                return 2 if result["status"] != "analysis_available" else 0
            else:
                from .reporting import report_from_config
                result = report_from_config(config)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, FileNotFoundError, KeyError) as exc:
        logging.error("%s: %s", type(exc).__name__, exc)
        return 1

