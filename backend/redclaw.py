#!/usr/bin/env python3
"""RedClaw File Tools JSON CLI. Host Python; independent from any AppImage lifetime."""
from __future__ import annotations

import argparse
import json
import os
import sys

import engine
import portable


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="redclaw-file-tools",
        description="Manage RedClaw File Tools extensions per file manager")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inventory")
    sub.add_parser("list")
    sub.add_parser("doctor")
    sub.add_parser("version")
    for cmd in ("plan", "install", "uninstall", "enable", "disable"):
        command = sub.add_parser(cmd)
        command.add_argument("--fm", required=True, choices=engine.SUPPORTED)
        command.add_argument("--slug", required=True)
        if cmd != "plan":
            command.add_argument("--yes", action="store_true")
        if cmd == "install":
            command.add_argument("--install-deps", action="store_true")
    operation = sub.add_parser("run")
    operation.add_argument("slug")
    operation.add_argument("action")
    operation.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    as_json = args.json
    try:
        if args.command == "inventory":
            data = engine.inventory()
        elif args.command == "list":
            catalog = engine.read_catalog()
            data = {"extensions": catalog["extensions"],
                    "file_managers": catalog["file_managers"]}
        elif args.command == "doctor":
            catalog = engine.read_catalog()
            fms = engine.detect_file_managers(catalog)
            data = {"file_managers": fms, "environment": {
                "python3": sys.version.split()[0],
                "state_path": str(engine.STATE),
                "payload_exists": engine.payload_dir().is_dir(),
            }}
        elif args.command == "version":
            data = {"product": "RedClaw File Tools",
                    "version": os.environ.get("REDCLAW_VERSION", "development")}
        elif args.command == "plan":
            data = engine.plan(args.fm, args.slug)
        elif args.command == "install":
            data = engine.install(args.fm, args.slug, install_deps=args.install_deps,
                                  confirmed=args.yes)
        elif args.command == "uninstall":
            data = engine.uninstall(args.fm, args.slug, confirmed=args.yes)
        elif args.command in ("enable", "disable"):
            data = engine.set_enabled(args.fm, args.slug,
                                      enabled=args.command == "enable",
                                      confirmed=args.yes)
        else:
            data = {"ok": True, "outputs": portable.run(args.slug, args.action, args.paths)}
        if as_json:
            print(json.dumps(data, ensure_ascii=False))
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, portable.ActionError) as exc:
        if as_json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"RedClaw File Tools: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
