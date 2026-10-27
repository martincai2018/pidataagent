# Copyright 2026 pidataagent contributors.
# Licensed under the Apache License, Version 2.0.
"""Pure renderers for pidataagent's local Datus config files.

IO and user interaction live in scripts/pidata_setup.py; keeping rendering
here makes it unit-testable without touching the filesystem.

Generated artifacts are all git-ignored:
- conf/agent.yml    provider credentials + the EDW datasource
- .datus/config.yml active provider/model + default datasource
"""

from __future__ import annotations

from typing import Literal

EDW_TYPES = ("starrocks", "doris")
EdwType = Literal["starrocks", "doris"]

DEFAULT_PROVIDER = "deepseek"
DEFAULT_MODEL = "deepseek-v4-pro"

_DATASOURCE_BLOCKS = {
    "starrocks": """\
      edw_starrocks:
        type: starrocks
        host: ${EDW_HOST}
        port: ${EDW_PORT}
        username: ${EDW_USER}
        password: ${EDW_PASSWORD}
        database: ${EDW_DATABASE}
""",
    "doris": """\
      edw_doris:
        type: doris
        host: ${EDW_HOST}
        port: ${EDW_PORT}
        username: ${EDW_USER}
        password: ${EDW_PASSWORD}
        database: ${EDW_DATABASE}
        catalog: internal
""",
}


def render_agent_yml(edw_type: EdwType) -> str:
    """Render the minimal project conf/agent.yml for one EDW datasource."""
    if edw_type not in _DATASOURCE_BLOCKS:
        raise ValueError(f"unsupported edw_type: {edw_type!r}; expected one of {EDW_TYPES}")
    return f"""\
agent:
  providers:
    deepseek:
      api_key: ${{DEEPSEEK_API_KEY}}
  # Chinese questions by default; temporal expressions parsed as zh.
  date_parsing:
    language: zh
  services:
    datasources:
{_DATASOURCE_BLOCKS[edw_type]}"""


def render_datus_config_yml(edw_type: EdwType, model: str = DEFAULT_MODEL) -> str:
    """Render .datus/config.yml: active target and default datasource."""
    if edw_type not in _DATASOURCE_BLOCKS:
        raise ValueError(f"unsupported edw_type: {edw_type!r}; expected one of {EDW_TYPES}")
    return f"""\
target:
  provider: {DEFAULT_PROVIDER}
  model: {model}
default_datasource: edw_{edw_type}
project_name: pidataagent
"""
