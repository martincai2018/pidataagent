#!/usr/bin/env python
# Copyright 2026 pidataagent contributors.
# Licensed under the Apache License, Version 2.0.
"""One-time local setup for pidataagent.

Generates three git-ignored artifacts:
  .env               real secrets
  conf/agent.yml     datasource/provider wiring (env placeholders)
  .datus/config.yml  active model + default datasource

Usage:
  .venv/Scripts/python.exe scripts/pidata_setup.py --edw starrocks
  .venv/Scripts/python.exe scripts/pidata_setup.py --edw doris --model deepseek-v4-flash

Values are taken from existing environment variables when present,
otherwise prompted (passwords and API key are hidden).
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pidata.config_templates import (  # noqa: E402
    DEFAULT_MODEL,
    EDW_TYPES,
    render_agent_yml,
    render_datus_config_yml,
)

ENV_KEYS = (
    "DEEPSEEK_API_KEY",
    "EDW_HOST",
    "EDW_PORT",
    "EDW_USER",
    "EDW_PASSWORD",
    "EDW_DATABASE",
)


def ask(prompt: str, *, secret: bool = False, default: str | None = None) -> str:
    shown = f"{prompt} [{default}]" if default is not None else prompt
    while True:
        value = getpass.getpass(f"{shown}: ") if secret else input(f"{shown}: ").strip()
        if not value and default is not None:
            return default
        if value:
            return value
        print("  value required, please retry")


def collect_env() -> dict[str, str]:
    env = {key: os.environ.get(key, "").strip() for key in ENV_KEYS}
    if not env["DEEPSEEK_API_KEY"]:
        env["DEEPSEEK_API_KEY"] = ask("DeepSeek API key (platform.deepseek.com)", secret=True)
    if not env["EDW_HOST"]:
        env["EDW_HOST"] = ask("EDW FE host, e.g. 10.0.0.1")
    if not env["EDW_PORT"]:
        env["EDW_PORT"] = ask("EDW FE MySQL-protocol port", default="9030")
    if not env["EDW_USER"]:
        env["EDW_USER"] = ask("read-only DB username")
    if not env["EDW_PASSWORD"]:
        env["EDW_PASSWORD"] = ask("DB password", secret=True)
    if not env["EDW_DATABASE"]:
        env["EDW_DATABASE"] = ask("default database/schema name")
    return env


def write_if_absent(rel_path: str, content: str, *, overwrite: bool) -> bool:
    path = ROOT / rel_path
    if path.exists() and not overwrite:
        print(f"skip (exists): {rel_path} (pass --overwrite to replace)")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote: {rel_path}")
    return True


def check_db(env: dict[str, str]) -> bool:
    try:
        import pymysql
    except ImportError:
        print("pymysql missing (install adapters first); skipping DB check")
        return True
    try:
        conn = pymysql.connect(
            host=env["EDW_HOST"],
            port=int(env["EDW_PORT"]),
            user=env["EDW_USER"],
            password=env["EDW_PASSWORD"],
            database=env["EDW_DATABASE"],
            connect_timeout=8,
        )
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
                assert row is not None and row[0] == 1
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001 - setup wizard surfaces any failure
        print(f"DB connectivity check FAILED: {exc}")
        print("Fix .env / network / read-only account, then re-run with --overwrite.")
        return False
    print("DB connectivity check OK (SELECT 1)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="pidataagent local setup")
    parser.add_argument("--edw", required=True, choices=EDW_TYPES)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    env = collect_env()

    env_body = "".join(f"{key}={env[key]}\n" for key in ENV_KEYS)
    write_if_absent(".env", env_body, overwrite=args.overwrite)
    write_if_absent("conf/agent.yml", render_agent_yml(args.edw), overwrite=args.overwrite)
    write_if_absent(
        ".datus/config.yml",
        render_datus_config_yml(args.edw, args.model),
        overwrite=args.overwrite,
    )

    ok = check_db(env)
    if ok:
        print("\nSetup complete. Smoke test:")
        print('  .venv/Scripts/datus.exe -p "列出当前数据库里所有的表"')
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
