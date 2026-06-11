# Metalearn Server

认知科学驱动的元学习引擎服务端。**SM-2 间隔重复**、学习路线管理、进度追踪、假懂检测、知识库 RAG。

## 安装

```bash
pip install -e .

# 带 HTTP API 支持
pip install -e ".[server]"

# 带知识库检索支持
pip install -e ".[knowledge]"

# 全部功能（开发）
pip install -e ".[dev]"
```

## CLI 使用

```bash
# 用户管理
meta-learn user create alice
meta-learn user list

# 学习路线
meta-learn track create 1 "线性代数" -t exam -p 5
meta-learn track list 1

# 知识点
meta-learn node add 1 "矩阵乘法" -i 5
meta-learn node list 1

# SM-2 复习（quality: 0=完全忘记 ~ 5=完美回忆）
meta-learn review create 1 -q 5

# 查询到期复习
meta-learn review due --user 1

# 今日学习安排
meta-learn schedule today --user 1 --minutes 120

# 知识库检索
meta-learn knowledge query "间隔重复原理"
meta-learn knowledge sources

# 仪表盘
meta-learn report dashboard 1

# 所有命令支持 --json 输出
meta-learn --json review due --user 1
```

## HTTP API

启动服务器：

```bash
# 首次启动：设置引导 API Key
export META_LEARN_BOOTSTRAP_KEY=ml_your_admin_key_here_change_this

python -m src.adapters.http_api.server
# → http://localhost:8000
# → OpenAPI 文档: http://localhost:8000/docs
```

所有 API 请求（除 `/health`）需携带 `Authorization: Bearer <key>` 头。
启动时可通过 `META_LEARN_BOOTSTRAP_KEY` 环境变量创建初始管理员 Key。

### 认证

| 端点 | 认证方式 |
|------|---------|
| `GET /health` | 公开，无需认证 |
| `GET/POST /api/v1/admin/keys` | 需管理员 Key |
| 所有其他端点 | 需有效 API Key（`Authorization: Bearer <key>`） |

### API Key 管理（需管理员 Key）

```bash
# 创建新 Key
POST /api/v1/admin/keys?display_name=user1&is_admin=false
Authorization: Bearer <admin-key>

# 列出所有 Key
GET /api/v1/admin/keys
Authorization: Bearer <admin-key>

# 吊销 Key
DELETE /api/v1/admin/keys/{id}
Authorization: Bearer <admin-key>
```

### 核心端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/users?name=xxx` | 创建用户 |
| GET | `/api/v1/users` | 用户列表 |
| POST | `/api/v1/tracks?user_id=&name=&type=` | 创建学习路线 |
| GET | `/api/v1/tracks?user_id=` | 路线列表 |
| POST | `/api/v1/nodes?track_id=&name=` | 添加知识点 |
| GET | `/api/v1/nodes?track_id=` | 知识点列表 |
| POST | `/api/v1/reviews` `{"node_id": N, "quality": 4}` | SM-2 复习 |
| GET | `/api/v1/reviews/due?user_id=` | 今日待复习 |
| GET | `/api/v1/schedule/today?user_id=&minutes=` | 今日安排 |
| GET | `/api/v1/dashboard?user_id=` | 仪表盘 |
| GET | `/api/v1/knowledge/sources` | 知识源列表 |
| POST | `/api/v1/knowledge/query` `{"query":"...","top_k":5}` | 知识检索 |
| GET | `/api/v1/tools` | OpenAI Function Calling 工具定义 |
| POST | `/api/v1/tools/execute` `{"name":"...","arguments":{}}` | 执行工具调用 |

### Docker

```bash
# 首次启动：设置引导 API Key
META_LEARN_BOOTSTRAP_KEY=ml_your_admin_key docker-compose up -d
# → http://localhost:8000
# → OpenAPI 文档: http://localhost:8000/docs
# 首次启动后，可通过 /api/v1/admin/keys 创建其他 Key
```

## OpenAI Function Calling

```python
import requests

API_KEY = "ml_your_key"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# 获取工具定义
resp = requests.get("http://localhost:8000/api/v1/tools", headers=HEADERS)
tools = resp.json()["tools"]

# 执行工具
resp = requests.post("http://localhost:8000/api/v1/tools/execute", json={
    "name": "knowledge_query",
    "arguments": {"query": "费曼技巧", "top_k": 3},
}, headers=HEADERS)
```

也可直接调用 Python API：

```python
from adapters.openai.tools import get_openai_tools, execute_tool

tools = get_openai_tools()
result = execute_tool("review_create", {"node_id": 1, "quality": 4})
```

## 架构

```
                    Agent Platforms (Claude Code / OpenAI / 豆包 / ...)
                    │          │              │
               ┌────┘     HTTP API      Function Calling
               │            │                 │
          CLI (meta-learn)  └──────┬──────────┘
               │                   │
          ┌────▼───────────────────▼────┐
          │   Metalearn Engine           │
          │   ┌──────────────────────┐  │
          │   │   Engine (纯 Python) │  │
          │   │  ├ SM-2, 假懂检测    │  │
          │   │  ├ SQLite DAO (7表)  │  │
          │   │  ├ 6-State FSM       │  │
          │   │  └ 多轨道调度器      │  │
          │   ├──────────────────────┤  │
          │   │  知识库 RAG (BM25)   │  │
          │   │  29 篇认知科学文档   │  │
          │   │  164 chunks, jieba   │  │
          │   └──────────────────────┘  │
          └────────────────────────────┘
```

### 目录结构

```
src/
├── engine/              # 核心引擎（平台无关）
│   ├── core/            # SM-2, FakeDetection, Indicators
│   ├── db/              # SQLite schema + 6 DAO
│   ├── workflow/        # 6-State Finite State Machine
│   └── scheduler/       # Multi-Track 时间分配
├── knowledge/           # 认知科学知识库 + BM25 索引
│   ├── core/            # 核心概念 (assessment, diagnosis, practice, teaching)
│   ├── methods/         # 学习方法 (active-recall, feynman, interleaving...)
│   ├── references/      # 参考资料 (citation-network, fake-detection...)
│   ├── strategies/      # 学习策略 (curriculum-design, combination...)
│   ├── examples/        # 示例对话 (feynman-session, diagnosis-interview...)
│   └── tracking/        # 追踪方法 (habit-tracking)
├── adapters/            # 平台适配层
│   ├── cli/             # CLI 入口 (meta-learn 命令)
│   ├── http_api/        # FastAPI REST API (含 auth)
│   ├── openai/          # OpenAI Function Calling 格式
│   └── claude_code/     # SKILL.md (metalearn 客户端 skill)
└── tests/               # 118 项测试
    ├── test_sm2.py, test_fake_detection.py, test_state_machine.py
    ├── test_dao_user.py, test_dao_track.py, test_dao_node.py
    ├── test_dao_review.py, test_dao_assessment_journal.py
    ├── test_scheduler.py, test_http_api.py, test_api_key.py
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 核心算法 | 纯 Python，零外部依赖 |
| 数据库 | SQLite + WAL 模式 |
| 知识检索 | BM25 (rank_bm25) + jieba 分词 |
| HTTP API | FastAPI + Uvicorn |
| 测试 | pytest (118 tests) |
| CI | GitHub Actions (3.10/3.11/3.12) |
| 部署 | Docker / docker-compose |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `META_LEARN_DB` | `~/.meta-learning/meta_learning.db` | SQLite 数据库路径 |
| `META_LEARN_BOOTSTRAP_KEY` | (无) | 首次启动时自动创建初始管理员 API Key |

## 开发

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check src/
```
