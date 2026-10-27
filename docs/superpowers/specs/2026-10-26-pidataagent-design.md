# pidataagent 设计文档

- 日期：2026-10-26
- 状态：已与项目所有者确认，待评审
- 上游基线：[Datus-ai/Datus-agent](https://github.com/Datus-ai/Datus-agent) v0.4.3（Apache-2.0）
- GitHub 仓库：`https://github.com/martincai2018/pidataagent`（**public**）

## 1. 项目目标

基于 Datus（开源 Data Engineering Agent）做薄分叉，构建面向 **Doris / StarRocks EDW** 的数据问数 Agent，使用 **DeepSeek** 作为 LLM，并提供**自建 Web 聊天界面**。

第一个里程碑（MVP）目标：在本地单机环境跑通完整闭环——

> Web 提问 → Agent 检索知识库 → 生成 Doris/StarRocks 方言 SQL → 只读执行 → 表格/图表展示 → 用户纠错沉淀回知识库。

连接已有的真实 Doris/StarRocks 实例（开发/测试库，只读账号）。存储使用 Datus 内置的 LanceDB + SQLite，不引入 PostgreSQL。

## 2. 关键决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 与上游关系 | **薄分叉**：vendored 源码，`datus/` 包名与核心代码保持不动 | 可持续 `git merge upstream/main`，同步新功能与 bugfix |
| 定制方式 | 全部走官方扩展点（skills、subagent/conf、adapter pip 包、import API） | 定制代码与上游零冲突 |
| LLM | DeepSeek（deepseek-chat，reasoner 可选） | SQL 能力强、性价比高；经 LiteLLM 接入 |
| EDW | Doris / StarRocks（上游已有 `datus-doris`、`datus-starrocks` 适配器） | 无需开发适配器，工作集中在测试验证与 Skill 调优 |
| 界面 | 自建 Web：Vite + React 18 + TypeScript + Ant Design + ECharts SPA | 数据问数组件齐全；可构建为静态文件由 FastAPI 单进程托管 |
| 后端 | `pidata/server` 薄 FastAPI 包装层，SSE 流式 | 不重新实现 agent 逻辑，只做协议适配与会话管理 |
| 数据环境 | 已有真实 Doris/StarRocks 实例 | 直接配连接，再导入 schema 与存量 SQL |
| 仓库可见性 | public | 不含真实连接串与业务数据；敏感配置仅存 `.env`/本地，不入库 |

## 3. 总体架构

```
┌────────────────────────────────────────────────────────┐
│  Web SPA (web/)  React 18 + TS + AntD + ECharts        │
│  对话 │ SQL 高亮 │ 结果表格 │ 图表 │ 反馈纠错            │
└──────────────┬─────────────────────────────────────────┘
               │ SSE 流式 (/api/chat, /api/sessions)
┌──────────────┴─────────────────────────────────────────┐
│  pidata/server  薄后端：FastAPI 包装层                  │
│  会话管理 · SSE 事件适配 · 静态文件托管 · 反馈写回 API   │
└──────────────┬─────────────────────────────────────────┘
               │ 直接 import datus.*（不 fork 核心代码）
┌──────────────┴─────────────────────────────────────────┐
│  Datus Agent Core（上游代码，保持不动）                 │
│  datus/agent: workflow / node / subagent                │
│  datus/tools: db_tools / sql_guard / skill_tools …      │
│  datus/models: LiteLLM → DeepSeek                       │
├─────────────────────────────────────────────────────────┤
│  Context Engine（上游，保持不动）                        │
│  LanceDB 向量 + tantivy 全文 + subject 业务域树          │
│  SQLite 会话；未来换 PostgreSQL 即可团队共享             │
├─────────────────────────────────────────────────────────┤
│  定制层（独立目录，merge 上游零冲突）                    │
│  .datus/skills/edw/ · subject/ 知识 · conf 覆盖         │
└──────────────┬─────────────────────────────────────────┘
               │ datus-doris / datus-starrocks 适配器
        ┌──────┴──────┐
   Doris / StarRocks（真实库，只读账号）
```

### 组件职责与边界

- **web/**：纯前端 SPA，只与 `pidata/server` 的 HTTP/SSE 接口对话，不直连数据库、不持有任何密钥。
- **pidata/server**：会话 CRUD、把 Datus 的流式事件转成 SSE、反馈写回、生产环境托管 `web/dist` 静态文件。不含业务推理逻辑。
- **datus/（vendored 上游）**：agent workflow、context engine、工具系统、模型适配。**本项目不修改此目录内任何文件**；如确需改动上游行为，优先通过配置/扩展点，其次向上游提 PR。
- **.datus/ + conf/**：EDW subagent、EDW skill、DeepSeek target、数据源声明。
- **subject/**：随仓库沉淀的知识库内容（语义模型、SQL 摘要）。**只放可公开的样例/脱敏内容**；真实业务知识默认通过本地 ingest 写入本地 LanceDB，是否入库随内容另行判断。
- **pidata/ingest/**：知识冷启动脚本（schema 抽取、存量 SQL 导入）。

## 4. 目录结构

```
pidataagent/
├── datus/                  # 上游源码（vendored，只跟随 upstream 更新）
├── conf/                   # 配置覆盖：agent.yml（DeepSeek provider、EDW subagent）
├── .datus/
│   ├── config.yml          # target=deepseek、default_datasource=edw
│   └── skills/
│       └── edw/            # EDW Skill
│           ├── SKILL.md
│           ├── dialect_rules/   # doris.md, starrocks.md
│           └── scripts/         # 辅助脚本（分区探查等，可选）
├── subject/                # Knowledge：semantic_models/、sql_summaries/
├── pidata/                 # 本项目自有 Python 代码
│   ├── server/             # FastAPI app、SSE 路由、静态托管
│   ├── ingest/             # 知识入库：schema 抽取、存量 SQL 导入
│   └── config.py
├── web/                    # Vite + React SPA（独立 package.json）
├── docs/                   # 架构文档、部署手册
├── pyproject.toml          # 上游原文件，保持不动，跟随 upstream 更新
├── uv.lock                 # 上游锁文件，保持不动
├── pidata-requirements.txt # 自有后端依赖（fastapi、uvicorn 等），用 uv pip install -r 安装
├── .env.example            # DEEPSEEK_API_KEY、EDW 连接串模板（真实 .env 不入库）
├── .gitignore
├── NOTICE                  # Apache-2.0 归属声明
└── README.md               # 注明 Fork 自 Datus-ai/Datus-agent
```

依赖策略：保留上游 `pyproject.toml` / `uv.lock` 不动（减少 merge 冲突），`uv sync` 安装上游依赖后，再用 `uv pip install -r pidata-requirements.txt` 安装 FastAPI 等自有依赖；`pidata/` 是仓库内顶级模块，直接 import，不单独打包发布。

Git 远端：

- `origin` → `https://github.com/martincai2018/pidataagent`
- `upstream` → `https://github.com/Datus-ai/Datus-agent`（不推送，仅 fetch/merge）

初始提交策略：导入上游 main 完整历史后，第一个自有提交为 NOTICE/README 及本设计文档，保证上游归属可追溯。

## 5. 关键数据流：问数闭环

1. 分析师在 Web 提问，例如「上季度华东区销售额 Top10 客户」。
2. `pidata/server` 创建/复用 Datus 会话，workflow 启动 EDW subagent。
3. Context Engine 按业务域树 + 向量检索 + 全文检索，命中客户/销售主题域的表结构、指标定义、参考 SQL。
4. DeepSeek 基于检索上下文与 EDW Skill 方言规则，生成 StarRocks/Doris 方言 SQL。
5. `sql_guard` 校验：仅允许 SELECT、强制 LIMIT、分区裁剪检查、禁止危险函数。
6. 适配器以只读账号执行 SQL；失败时进入上游自带的纠错重试节点（带上报错重新生成，次数上限可配）。
7. 结果经 SSE 逐段推送前端：思考步骤 → SQL → 结果集 → 图表推荐。
8. 用户点「采纳 / 纠错」：反馈写入上游 `storage/feedback` 与参考 SQL 存储，后续检索可命中——越用越准。

## 6. Knowledge 知识冷启动

- **表结构**：`pidata/ingest` 脚本连接真实库，读取 information_schema 以及分区/分桶/属性信息，写入 schema_metadata。
- **存量 SQL**：收集团队常用查询脚本与调度平台 SQL，清洗（去敏、去临时库引用、补业务描述）后写入 sql_summaries / reference SQL。
- **业务术语表**：人工维护指标口径（例：销售额 = 已支付订单金额 − 退款），作为 EDW subagent 的 curated context。
- **语义模型**：闭环跑通后，使用 Datus 自动语义建模生成 OSI 模型并人工校对。
- public 仓库纪律：入库内容必须脱敏；真实库主机、账号、业务 SQL 默认只进本地存储（`~/.datus/data/...`），不提交到 git。

## 7. EDW Skill 内容（`.datus/skills/edw/`）

以 Markdown 规则为主（MVP 不写自定义 Python tool；规则不够用时再按上游扩展点新增 tool）：

- Doris 与 StarRocks 的方言差异：日期函数、窗口函数、`LIMIT` 语义、类型转换。
- 强制规则：**必须带分区过滤**、大表查询必须 LIMIT、禁止 `SELECT *` 扫宽表。
- 性能规则：分桶键/Colocate Join 优先、合理利用物化视图与 rollup、避免 shuffle 倾斜的写法。
- 典型查询范式：TopN、同环比、漏斗、留存、维度下钻。
- 方言选择：数据源为 Doris 或 StarRocks 时分别加载对应规则文件。

## 8. 错误处理与安全

- 数据库使用**只读账号**；sql_guard 拦截一切非 SELECT 语句；默认结果上限 1000 行。
- LLM/DB 错误通过 SSE 以明确的人类可读消息推送前端；SQL 重试次数设上限，防止死循环消耗 token。
- `DEEPSEEK_API_KEY` 与 EDW 连接串仅存 `.env`（`.env.example` 提供模板），`.gitignore` 保证不入库。
- Web 后端 MVP 仅监听 localhost；CORS 只允许本地 dev server 来源。
- public 仓库：提交前检查不包含任何内网地址、账号、真实业务 SQL；ingest 产物默认写本地存储而非仓库。

## 9. 测试策略

- `pidata/` 自有代码：pytest（`@pytest.mark.asyncio`）+ ruff，沿用上游规范（line-length 120、isort 分组、类型注解、Pydantic）。
- ingest 脚本：以录制的 schema 样本作为测试夹具，不依赖真实库即可跑单测。
- 端到端黄金测试集：准备 10–20 条标准业务问题，在真实 Doris/StarRocks 开发库上验证「生成 SQL 可执行率」与结果正确性，作为 M4 验收门槛。
- 前端：MVP 以手工验收为主，关键组件（SQL 块、结果表格、SSE 解析）配基础单测。

## 10. 里程碑

| 阶段 | 内容 | 完成标准 |
|---|---|---|
| M0 仓库奠基 | 创建 public GitHub 仓库；vendor 上游源码并配双 remote；NOTICE/README；uv + Python 3.12 环境；DeepSeek 与 Doris/StarRocks 在 CLI 跑通 | 初始提交已推送；CLI 能问数 |
| M1 知识冷启动 | schema/存量 SQL 入库脚本、EDW Skill v1、业务术语表 | CLI 下黄金问题集 SQL 可执行率 ≥ 80% |
| M2 后端 | `pidata/server` FastAPI：会话管理、对话 SSE、反馈写回、静态托管 | API（含流式）可调通 |
| M3 Web SPA | 对话页、SQL 高亮块、结果表格、ECharts、反馈按钮，`npm run build` 由 FastAPI 托管 | 浏览器内完整闭环 |
| M4 验收 | 黄金问题集执行、README/部署文档、public 仓库脱敏复查 | MVP 交付 |

M0 完成即推送初始提交；M1 起每阶段结束推送一次。

## 11. 环境备注

- 本机当前 Python 为 3.14；上游依赖（lancedb 0.34、固定版 pandas/pyarrow 等）要求 3.12。使用 **uv 管理环境**，由 `requires-python >=3.12,<3.13` 触发 uv 自动安装 Python 3.12，不改动系统 Python。
- Node.js v24 已就绪，满足 Vite 前端要求。
- `gh` CLI 已以 martincai2018 登录，具备 `repo` scope，可直接创建仓库与推送。

## 12. 显式不做（YAGNI）

- 不做 PostgreSQL 共享存储、多用户鉴权、会话隔离（团队服务器阶段再议）。
- 不做飞书/钉钉机器人、调度器集成、Superset/Grafana 双向集成。
- 不做自动语义建模的深度定制（先用上游原生能力）。
- 不重命名 `datus` 包、不 rebrand 源码内部。
- 不开发新数据库适配器（Doris/StarRocks 已有官方适配器）。
