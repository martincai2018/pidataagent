# M0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Datus 上游源码 vendored 进 public 仓库 `martincai2018/pidataagent`，搭好 Python 3.12 + uv 环境与 Doris/StarRocks 适配器，接通 DeepSeek，在 CLI 用自然语言对真实 EDW 完成一次端到端问数。

**Architecture:** 薄分叉——`datus/` 上游代码一行不改，双 remote（`origin` 自有、`upstream` 只拉不推），自有代码全部放在 `pidata/`、`scripts/`、`docs/pidataagent/` 等上游不存在的路径，保证 `git merge upstream/main` 无冲突。本地密钥与数据源配置走 `.env` + `conf/agent.yml` + `.datus/config.yml`（三者均已被上游 .gitignore 忽略），仓库只提交模板与生成器。

**Tech Stack:** git / GitHub CLI（gh）、uv + CPython 3.12（uv 自动下载）、datus-agent 0.4.3（vendored）、datus-starrocks 0.1.12 / datus-doris 0.1.3（PyPI，entry-point 自动注册）、DeepSeek（内置 provider，env `DEEPSEEK_API_KEY`）、pytest + ruff。

**Spec:** [docs/superpowers/specs/2026-10-26-pidataagent-design.md](../specs/2026-10-26-pidataagent-design.md)

**环境事实（已核实）：**

- CLI 非交互单次提问：`datus -p "问题"`，输出 MessagePayload JSON lines（normal profile 下 SELECT 自动放行，无需人工批准）。
- 数据源配置在 `conf/agent.yml` 的 `agent.services.datasources`，支持 `${ENV_VAR}` 占位；`.datus/config.yml` 白名单键：`target`、`default_datasource`、`project_name`。
- DeepSeek 已在 `conf/providers.yml` 内置，当前模型 `deepseek-v4-pro` / `deepseek-v4-flash`。
- `.env`、`.datus/`、`conf/agent.yml`、`subject/` 均已被上游 .gitignore 忽略。
- 首次运行会经 fastembed 下载 all-MiniLM-L6-v2 模型（约 90MB）。
- Datus 启动时 `agent_config_loader` 会 `load_dotenv()`，CWD 下 `.env` 自动生效，无需手动 export。
- 上游 `tests/` 是带 `__init__.py` 的包，新增测试子目录也必须放 `__init__.py`。
- 本机 Windows + Git Bash；`gh` 已登录 martincai2018；Node v24（M0 不用）。

---

## File Structure

M0 结束后仓库新增/产生以下路径：

| 路径 | 归属 | 职责 |
|---|---|---|
| `datus/` 及上游全部文件 | vendored（跟随 upstream，不改） | Agent 核心 |
| `.python-version` | 我们，提交 | 内容 `3.12`，让 uv 自动获取并锁定 CPython 3.12 |
| `NOTICE` | 我们，提交 | Apache-2.0 归属声明 |
| `README.md` 顶部 banner | 我们，修改（有标记，merge 后可重放） | 声明本仓库是薄分叉 |
| `pidata-requirements.txt` | 我们，提交 | 适配器等上游 lock 之外的附加依赖 |
| `docs/upstream-sync.md` | 我们，提交 | 上游同步流程与注意事项 |
| `docs/pidataagent/SETUP.md` | 我们，提交 | 中文安装与冒烟手册 |
| `pidata/__init__.py` | 我们，提交 | 自有 Python 包 |
| `pidata/config_templates.py` | 我们，提交 | 纯函数：渲染 agent.yml / .datus/config.yml（可单测） |
| `tests/pidata/__init__.py` | 我们，提交 | 空文件，使测试目录成为包（对齐上游 tests 布局） |
| `tests/pidata/test_config_templates.py` | 我们，提交 | 模板渲染单测 |
| `.env.example` | 我们，提交 | 环境变量模板（无密钥） |
| `scripts/pidata_setup.py` | 我们，提交 | 一次性本地配置向导（IO 层，调用模板函数），含 DB `SELECT 1` 连通性检查 |
| `.env`、`conf/agent.yml`、`.datus/config.yml` | 本地生成，**不提交** | 真实配置与密钥 |

---

## Task 1: Vendor 上游源码并创建 GitHub 仓库

**Files:**
- 无自有文件；本任务只做 git 操作。

- [ ] **Step 1: 添加上游 remote 并拉取**

```bash
git remote add upstream https://github.com/Datus-ai/Datus-agent.git
git fetch upstream --tags
git tag upstream-sync-2026-10-26 upstream/main
```

Expected: fetch 完成（仓库历史约 140MB），无报错。

- [ ] **Step 2: 合并不相关历史（保留上游全部 commit）**

```bash
git merge upstream/main --allow-unrelated-histories --no-edit
```

Expected: 自动合并成功。我们仅有 `docs/superpowers/specs/...`，上游 `docs/` 下无同路径文件，**不应出现冲突**；若出现冲突，停止并人工检查，不要用 `-X` 策略掩盖。

- [ ] **Step 3: 验证 vendored 完整性**

```bash
ls datus/ | head -5
git log --oneline | head -5
```

Expected: 能看到 `__init__.py  agent  api  auth  cli ...`；log 顶部是 merge commit，下面既有上游提交也有我们的 spec 提交。

- [ ] **Step 4: 创建 public GitHub 仓库并推送（含双 remote 验证）**

```bash
gh repo create pidataagent --public --source=. --remote=origin \
  --description "Data agent for Doris/StarRocks EDW, thin fork of Datus (DeepSeek + web UI)" --push
git remote -v
```

Expected: 输出 `https://github.com/martincai2018/pidataagent` 创建成功并完成推送；`git remote -v` 显示 `origin`（push 目标）与 `upstream`（fetch 用）两个远端。在浏览器打开仓库确认能看到完整历史与 `datus/` 目录。

---

## Task 2: 归属声明与工程基线文件

**Files:**
- Create: `NOTICE`
- Modify: `README.md`（仅文件最顶部插入带标记的 banner）
- Create: `.python-version`
- Create: `pidata-requirements.txt`
- Create: `docs/upstream-sync.md`

- [ ] **Step 1: 创建 NOTICE**

`NOTICE` 完整内容：

```text
pidataagent
Copyright 2026 pidataagent contributors

This product includes software developed by the Datus project
(https://github.com/Datus-ai/Datus-agent), licensed under the Apache
License, Version 2.0.

A verbatim copy of the Datus source code is bundled in the datus/
directory. Copyright headers in those files are retained unchanged.
The original project is the copyright holder of that bundled code.
```

- [ ] **Step 2: 在 README.md 最顶部插入 fork banner**

在 `README.md` 第 1 行之前插入（两条 HTML 注释是重放标记，merge 上游后若该块丢失，按此原样补回）：

```markdown
<!-- pidataagent:fork-banner:start -->
> **pidataagent** is a thin fork of [Datus-ai/Datus-agent](https://github.com/Datus-ai/Datus-agent) (Apache-2.0), customized for Doris/StarRocks EDW with DeepSeek and a self-built web UI. Upstream code under `datus/` is kept unmodified. Start here: [docs/pidataagent/SETUP.md](docs/pidataagent/SETUP.md) · Attribution: [NOTICE](NOTICE)
<!-- pidataagent:fork-banner:end -->

```

- [ ] **Step 3: 创建 .python-version（锁定 uv 使用 3.12）**

`.python-version` 内容（单行，无引号）：

```text
3.12
```

- [ ] **Step 4: 创建 pidata-requirements.txt（上游 lock 之外的附加依赖）**

`pidata-requirements.txt` 完整内容：

```text
# Installed with: uv pip install -r pidata-requirements.txt
# Re-run after `uv sync` (use `uv sync --inexact` to keep these packages).
# DB adapters auto-register via the "datus.adapters" entry-point group.
datus-starrocks==0.1.12
datus-doris==0.1.3
```

- [ ] **Step 5: 创建 docs/upstream-sync.md**

`docs/upstream-sync.md` 完整内容：

````markdown
# Syncing upstream Datus changes

This repo is a thin fork of <https://github.com/Datus-ai/Datus-agent>.
All custom code lives outside `datus/` (see `pidata/`, `scripts/`,
`docs/pidataagent/`, `pidata-requirements.txt`); the vendored `datus/`
tree is never edited locally.

```bash
git fetch upstream --tags
git tag upstream-sync-$(date +%Y-%m-%d) upstream/main
git merge upstream/main --no-edit
uv sync --inexact
uv pip install -r pidata-requirements.txt
uv run pytest tests/pidata -v
```

Notes:

- If `README.md` conflicts, re-apply the block between
  `pidataagent:fork-banner:start/end` markers and keep the upstream body.
- Never commit `conf/agent.yml`, `.datus/`, `.env`, or `subject/` —
  upstream `.gitignore` already excludes them.
- Review upstream release notes for adapter version bumps, then update
  pins in `pidata-requirements.txt`.
````

- [ ] **Step 6: 提交并推送**

```bash
git add NOTICE README.md .python-version pidata-requirements.txt docs/upstream-sync.md
git commit -m "chore: add fork attribution, py3.12 pin, adapter requirements

Co-Authored-By: Claude <noreply@anthropic.com>"
git push
```

Expected: commit 成功；`git status` 干净。

---

## Task 3: uv 环境、Python 3.12 与 EDW 适配器

**Files:**
- 无提交物（产物在 `.venv/`，已被忽略）。

- [ ] **Step 1: 确认/安装 uv**

```bash
uv --version
```

Expected: 打印 uv 版本。若报 command not found，执行 `python -m pip install --user uv` 后重开终端再验证。

- [ ] **Step 2: 同步上游依赖（uv 会自动下载 CPython 3.12）**

```bash
uv sync --inexact
```

Expected: 首次会下载 Python 3.12 与大量 wheel（lancedb、pyarrow、fastembed 等），耗时数分钟到十几分钟。结束时创建 `.venv/`。

- [ ] **Step 3: 验证 Python 版本确为 3.12**

```bash
uv run python --version
```

Expected: `Python 3.12.x`（不是 3.14；`.python-version` 生效）。

- [ ] **Step 4: 安装 Doris/StarRocks 适配器**

```bash
uv pip install -r pidata-requirements.txt
```

Expected: 安装 `datus-starrocks`、`datus-doris` 及其依赖（`datus-mysql`、`pymysql` 等）。

- [ ] **Step 5: 验证适配器 entry-point 注册与 CLI 可用**

```bash
uv run python -c "from importlib.metadata import entry_points; eps=entry_points(group='datus.adapters'); print(sorted(e.name for e in eps))"
uv run datus --version
```

Expected: 第一行输出的列表中包含 `doris` 和 `starrocks`；第二行输出 `Datus CLI 0.4.3`（或更新的 vendored 版本）。若列表为空，说明适配器装进了别的环境，确认命令前缀是 `uv run`。

---

## Task 4: 配置模板渲染（TDD）

**Files:**
- Create: `pidata/__init__.py`
- Create: `pidata/config_templates.py`
- Test: `tests/pidata/test_config_templates.py`

- [ ] **Step 1: 写失败的测试**

先建包目录（`tests/pidata/__init__.py` 为空文件，上游 `tests/` 是包结构）：

```bash
mkdir -p tests/pidata pidata
touch tests/pidata/__init__.py
```

`pidata/__init__.py` 完整内容：

```python
"""pidataagent custom code (everything outside the vendored datus/ tree)."""
```

`tests/pidata/test_config_templates.py` 完整内容：

```python
import pytest
import yaml

from pidata.config_templates import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    render_agent_yml,
    render_datus_config_yml,
)


def test_render_agent_yml_starrocks():
    cfg = yaml.safe_load(render_agent_yml("starrocks"))
    agent = cfg["agent"]
    assert agent["providers"]["deepseek"]["api_key"] == "${DEEPSEEK_API_KEY}"
    assert agent["date_parsing"]["language"] == "zh"
    ds = agent["services"]["datasources"]["edw_starrocks"]
    assert ds == {
        "type": "starrocks",
        "host": "${EDW_HOST}",
        "port": "${EDW_PORT}",
        "username": "${EDW_USER}",
        "password": "${EDW_PASSWORD}",
        "database": "${EDW_DATABASE}",
    }


def test_render_agent_yml_doris_uses_internal_catalog():
    cfg = yaml.safe_load(render_agent_yml("doris"))
    ds = cfg["agent"]["services"]["datasources"]["edw_doris"]
    assert ds["type"] == "doris"
    assert ds["catalog"] == "internal"
    assert "edw_starrocks" not in cfg["agent"]["services"]["datasources"]


def test_render_agent_yml_rejects_unknown_type():
    with pytest.raises(ValueError, match="edw_type"):
        render_agent_yml("mysql")


def test_render_datus_config_yml_starrocks():
    cfg = yaml.safe_load(render_datus_config_yml("starrocks"))
    assert cfg["target"] == {"provider": DEFAULT_PROVIDER, "model": DEFAULT_MODEL}
    assert cfg["default_datasource"] == "edw_starrocks"
    assert cfg["project_name"] == "pidataagent"


def test_render_datus_config_yml_doris():
    cfg = yaml.safe_load(render_datus_config_yml("doris", model="deepseek-v4-flash"))
    assert cfg["default_datasource"] == "edw_doris"
    assert cfg["target"]["model"] == "deepseek-v4-flash"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/pidata -v
```

Expected: FAIL，`ModuleNotFoundError: No module named 'pidata.config_templates'`。

- [ ] **Step 3: 实现模板渲染**

`pidata/config_templates.py` 完整内容：

```python
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
        raise ValueError(
            f"unsupported edw_type: {edw_type!r}; expected one of {EDW_TYPES}"
        )
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
        raise ValueError(
            f"unsupported edw_type: {edw_type!r}; expected one of {EDW_TYPES}"
        )
    return f"""\
target:
  provider: {DEFAULT_PROVIDER}
  model: {model}
default_datasource: edw_{edw_type}
project_name: pidataagent
"""
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/pidata -v
```

Expected: 5 passed。

- [ ] **Step 5: ruff 检查与提交**

```bash
uv run ruff format pidata/ tests/pidata/
uv run ruff check pidata/ tests/pidata/
git add pidata/ tests/pidata/
git commit -m "feat: add config template renderers with tests

Co-Authored-By: Claude <noreply@anthropic.com>"
```

Expected: ruff 无报错（line-length 120）；commit 成功。

---

## Task 5: 环境变量模板与一键配置脚本

**Files:**
- Create: `.env.example`
- Create: `scripts/pidata_setup.py`

- [ ] **Step 1: 创建 .env.example**

`.env.example` 完整内容：

```text
# Copy to .env (git-ignored) or let scripts/pidata_setup.py create it.
# DeepSeek: https://platform.deepseek.com/api_keys
DEEPSEEK_API_KEY=
# MySQL-protocol port is 9030 for both Doris FE and StarRocks FE.
EDW_HOST=
EDW_PORT=9030
EDW_USER=
EDW_PASSWORD=
EDW_DATABASE=
```

- [ ] **Step 2: 编写 scripts/pidata_setup.py**

`scripts/pidata_setup.py` 完整内容：

```python
#!/usr/bin/env python
# Copyright 2026 pidataagent contributors.
# Licensed under the Apache License, Version 2.0.
"""One-time local setup for pidataagent.

Generates three git-ignored artifacts:
  .env               real secrets
  conf/agent.yml     datasource/provider wiring (env placeholders)
  .datus/config.yml  active model + default datasource

Usage:
  uv run python scripts/pidata_setup.py --edw starrocks
  uv run python scripts/pidata_setup.py --edw doris --model deepseek-v4-flash

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


def ask(name: str, prompt: str, *, secret: bool = False, default: str | None = None) -> str:
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
        env["DEEPSEEK_API_KEY"] = ask(
            "DEEPSEEK_API_KEY", "DeepSeek API key (platform.deepseek.com)", secret=True
        )
    if not env["EDW_HOST"]:
        env["EDW_HOST"] = ask("EDW_HOST", "EDW FE host, e.g. 10.0.0.1")
    if not env["EDW_PORT"]:
        env["EDW_PORT"] = ask("EDW_PORT", "EDW FE MySQL-protocol port", default="9030")
    if not env["EDW_USER"]:
        env["EDW_USER"] = ask("EDW_USER", "read-only DB username")
    if not env["EDW_PASSWORD"]:
        env["EDW_PASSWORD"] = ask("EDW_PASSWORD", "DB password", secret=True)
    if not env["EDW_DATABASE"]:
        env["EDW_DATABASE"] = ask("EDW_DATABASE", "default database/schema name")
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
        print('  uv run datus -p "列出当前数据库里所有的表"')
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: 静态检查并提交**

```bash
uv run ruff format scripts/pidata_setup.py
uv run ruff check scripts/pidata_setup.py
git add .env.example scripts/pidata_setup.py
git commit -m "feat: add local setup wizard and env template

Co-Authored-By: Claude <noreply@anthropic.com>"
git push
```

Expected: ruff 通过；commit 成功；`.env` 不出现在 `git status` 中（被上游 .gitignore 忽略）。

---

## Task 6: 接入真实 EDW 并完成端到端冒烟（需要真实凭据，人工检查点）

**Files:**
- 生成本地 `.env`、`conf/agent.yml`、`.datus/config.yml`（均不提交）。

- [ ] **Step 1: 运行配置向导（二选一，按实际引擎）**

```bash
uv run python scripts/pidata_setup.py --edw starrocks
# 或：uv run python scripts/pidata_setup.py --edw doris
```

Expected: 交互式输入 DeepSeek key 与 EDW 只读账号信息；结束打印 `DB connectivity check OK (SELECT 1)`。若失败，按报错修正后加 `--overwrite` 重跑。

- [ ] **Step 2: 确认密钥文件未被 git 跟踪**

```bash
git status --short --ignored | grep -E "\.env$|conf/agent.yml|\.datus/config.yml"
```

Expected: 三个文件都带 `!!`（ignored）前缀。

- [ ] **Step 3: 端到端问数冒烟（会消耗少量 DeepSeek token）**

```bash
uv run datus -p "列出当前数据库里所有的表"
```

Expected: stdout 输出多行 JSON（MessagePayload）；其中包含生成的 SQL（`SHOW TABLES` 或查询 `information_schema`）以及返回的表名列表；进程退出码为 0。首次运行会下载 embedding 模型（约 90MB）。

若 embedding 模型在国内网络下载失败：

```bash
HF_ENDPOINT=https://hf-mirror.com uv run datus -p "列出当前数据库里所有的表"
```

- [ ] **Step 4: 再来一条带业务语义的问题（人工核对结果）**

```bash
uv run datus -p "这个库里一共有多少张表？"
```

Expected: 返回数字且与 Step 3 的表数量一致。至此 M0 闭环验证通过（知识库尚未冷启动，复杂业务问题留给 M1）。

---

## Task 7: 安装手册与 M0 收尾

**Files:**
- Create: `docs/pidataagent/SETUP.md`

- [ ] **Step 1: 编写中文安装手册**

`docs/pidataagent/SETUP.md` 完整内容：

````markdown
# pidataagent 安装与冒烟（M0）

面向在本机把 pidataagent 跑起来并连上真实 Doris/StarRocks 的开发者。

## 前置条件

- Windows / macOS / Linux，已装 Git Bash（Windows）、git、GitHub CLI（gh，已登录）
- [uv](https://docs.astral.sh/uv/)（没有则 `python -m pip install --user uv`）
- DeepSeek API Key：<https://platform.deepseek.com/api_keys>
- Doris 或 StarRocks 的 FE 主机地址、**只读账号**、库名（MySQL 协议，默认端口 9030）

## 安装

```bash
git clone https://github.com/martincai2018/pidataagent.git
cd pidataagent
uv sync --inexact                       # 首次会自动下载 Python 3.12
uv pip install -r pidata-requirements.txt
```

## 配置

```bash
uv run python scripts/pidata_setup.py --edw starrocks   # 或 --edw doris
```

按提示输入密钥。脚本生成本地且不入库的三个文件：`.env`、
`conf/agent.yml`、`.datus/config.yml`，并执行 `SELECT 1` 验证连通。

切换模型：编辑 `.datus/config.yml` 的 `target.model`
（可选值：`deepseek-v4-pro`、`deepseek-v4-flash`），或在 CLI 中用 `/model`。

## 冒烟

```bash
uv run datus -p "列出当前数据库里所有的表"
```

输出为 MessagePayload JSON 流，包含生成的 SQL 与结果集。
首次运行下载本地 embedding 模型（约 90MB）；国内网络可加
`HF_ENDPOINT=https://hf-mirror.com`。

交互式会话直接运行 `uv run datus`。

## 同步上游

见 [../../upstream-sync.md](../upstream-sync.md)。

## 安全约定

- 数据库账号只读；`datus/` 上游 sql_guard 与权限系统默认只放行 SELECT。
- 密钥只写 `.env`，不要提交；public 仓库中不放入任何真实主机、账号、业务 SQL。
````

- [ ] **Step 2: 提交、打 M0 标签并推送**

```bash
git add docs/pidataagent/SETUP.md
git commit -m "docs: add M0 setup guide

Co-Authored-By: Claude <noreply@anthropic.com>"
git tag m0-foundation
git push && git push origin m0-foundation
```

Expected: GitHub 上出现 `m0-foundation` tag，M0 完成。下一阶段 M1（知识冷启动 + EDW Skill）另写计划。
