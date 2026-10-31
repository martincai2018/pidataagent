# pidataagent 安装与冒烟（M0）

面向在本机把 pidataagent 跑起来并连上真实 Doris/StarRocks 的开发者。

## 前置条件

- Windows（本机路径以 Git Bash 为例；macOS/Linux 将 `.venv/Scripts/xxx` 换为 `.venv/bin/xxx`）
- 已装 git、GitHub CLI（gh）、[uv](https://docs.astral.sh/uv/)（没有则 `python -m pip install --user uv`）
- DeepSeek API Key：<https://platform.deepseek.com/api_keys>
- Doris 或 StarRocks 的 FE 主机地址、**只读账号**、库名（MySQL 协议，默认端口 9030）

## 安装

```bash
git clone https://github.com/martincai2018/pidataagent.git
cd pidataagent

# 首次会自动下载 Python 3.12（.python-version 已锁定）。
# Windows 上必须跳过 dosi-engine：它只发布 Linux/macOS wheel。
# 跳过不影响 NL→SQL 问数；仅 Dosi 语义层（AskMetrics/OSI 编译）在 Windows 不可用。
uv sync --inexact --no-install-package dosi-engine

# 安装 Doris/StarRocks 适配器（顺序在 sync 之后；不要再重跑 uv sync，
# 否则会把 datus-db-core 降回锁文件版本）。
uv pip install -r pidata-requirements.txt
```

> 网络较慢时，可在 uv 命令前临时使用清华镜像（不写入任何配置文件）：
> `UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple uv sync --inexact --no-install-package dosi-engine`

验证安装：

```bash
.venv/Scripts/python.exe --version          # 应为 Python 3.12.x
.venv/Scripts/datus.exe --version            # 应打印 Datus CLI 版本
.venv/Scripts/python.exe -c "from importlib.metadata import entry_points; print(sorted(e.name for e in entry_points(group='datus.adapters')))"
# 输出列表中应包含 doris、starrocks
```

## 配置

```bash
# StarRocks：
.venv/Scripts/python.exe scripts/pidata_setup.py --edw starrocks
# Doris：
.venv/Scripts/python.exe scripts/pidata_setup.py --edw doris
# 可选：--model deepseek-v4-flash（默认 deepseek-v4-pro）；重新配置加 --overwrite
```

按提示输入 DeepSeek Key 与 EDW 只读账号（密钥不回显）。脚本生成三个**本地且不入库**的文件：
`.env`、`conf/agent.yml`、`.datus/config.yml`，并自动执行 `SELECT 1` 验证数据库连通性。

> Windows 上请始终使用 `.venv/Scripts/` 下的可执行文件；不要用裸 `uv run`
> （它会触发自动 sync 并重新报 dosi-engine 平台错误）。`uv run --no-sync` 也可以。

## 冒烟

```bash
.venv/Scripts/datus.exe -p "列出当前数据库里所有的表"
```

输出为 MessagePayload JSON 流，包含生成的 SQL 与结果集；退出码 0 即端到端打通。
首次运行会下载本地 embedding 模型（约 90MB）；国内网络可走镜像：

```bash
HF_ENDPOINT=https://hf-mirror.com .venv/Scripts/datus.exe -p "列出当前数据库里所有的表"
```

交互式会话直接运行 `.venv/Scripts/datus.exe`。

## 同步上游

见 [upstream-sync.md](../upstream-sync.md)（本仓库是 GitHub fork + 本地浅克隆）。

## 安全约定

- 数据库账号只读；Datus 权限系统默认只放行 SELECT（SHOW/DESCRIBE/EXPLAIN）。
- 密钥只写 `.env`，`.env`、`conf/agent.yml`、`.datus/`、`subject/` 均已被 .gitignore 忽略，不要提交。
- public 仓库中不要放入任何真实主机、账号、业务 SQL。
