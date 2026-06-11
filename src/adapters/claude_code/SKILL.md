---
name: metalearn
description: "云端元学习服务 — 通过 HTTP API 远程调用元学习引擎（SM-2 间隔重复、学习路线管理、进度追踪）。需服务器地址和 API Key。涉及词：'学习计划'、'备考'、'考试'、'复习'、'知识体系'、'深度学习'、'检测理解'。"
---

# Metalearn API 客户端

Metalearn Server 的客户端 Skill。通过 HTTP API 远程调用元学习引擎（无需本地安装）。

**运行方式**：向 Metalearn Server 发送 HTTP 请求完成所有操作。

## 前置条件

使用本 skill 需要两样东西：
- **服务器地址**（如 `https://learn.example.com`）
- **API Key**（服务端管理员分配的 `ml_` 开头的密钥）

如用户未提供，先主动询问。获取后在整个对话中使用。

## 核心教育哲学

1. 主动提取 > 被动复习
2. 适度困难 > 流畅体验
3. 真正理解 = 可压缩 + 可迁移
4. 知识结构组织形态 > 零散正确答案

## API 调用规范

所有请求需携带认证头：
```
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

基础 URL 记为 `{BASE}`。

## 端点速查

### 用户管理

| 操作 | 请求 |
|------|------|
| 创建用户 | `POST {BASE}/api/v1/users?name=xxx&display_name=xxx` |
| 用户列表 | `GET {BASE}/api/v1/users` |
| 获取用户 | `GET {BASE}/api/v1/users/{id}` |
| 删除用户 | `DELETE {BASE}/api/v1/users/{id}` |

### 学习路线

| 操作 | 请求 |
|------|------|
| 创建路线 | `POST {BASE}/api/v1/tracks` body: `{"user_id":1, "name":"线性代数", "type":"exam", "priority":5}` |
| 路线列表 | `GET {BASE}/api/v1/tracks?user_id=1` |
| 更新路线 | `PATCH {BASE}/api/v1/tracks/{id}` body: `{"name":"...", "status":"active"}` |

### 知识点

| 操作 | 请求 |
|------|------|
| 添加节点 | `POST {BASE}/api/v1/nodes` body: `{"track_id":1, "name":"矩阵乘法", "importance":5, "level":1}` |
| 节点列表 | `GET {BASE}/api/v1/nodes?track_id=1` |
| 删除节点 | `DELETE {BASE}/api/v1/nodes/{id}` |

### SM-2 复习

| 操作 | 请求 |
|------|------|
| 执行复习 | `POST {BASE}/api/v1/reviews` body: `{"node_id":1, "quality":4}` |
| 待复习 | `GET {BASE}/api/v1/reviews/due?user_id=1` |
| 复习统计 | `GET {BASE}/api/v1/reviews/stats?track_id=1` |

### 知识检索

| 操作 | 请求 |
|------|------|
| 检索知识库 | `POST {BASE}/api/v1/knowledge/query` body: `{"query":"间隔重复原理", "top_k":5}` |
| 知识源列表 | `GET {BASE}/api/v1/knowledge/sources` |

### 日程 & 仪表盘

| 操作 | 请求 |
|------|------|
| 今日安排 | `GET {BASE}/api/v1/schedule/today?user_id=1&minutes=120` |
| 仪表盘 | `GET {BASE}/api/v1/dashboard?user_id=1` |

### 学习日志 & 评估

| 操作 | 请求 |
|------|------|
| 记录日志 | `POST {BASE}/api/v1/journals` body: `{"user_id":1, "focus":60, "topics":["矩阵"], "methods":["费曼"]}` |
| 查询日志 | `GET {BASE}/api/v1/journals?user_id=1&date=2026-06-11` |
| 记录评估 | `POST {BASE}/api/v1/assessments` body: `{"user_id":1, "track_id":1, "after":3, "duration":30}` |

## 动态工具发现（推荐）

`{BASE}/api/v1/tools` 端点返回 OpenAI Function Calling 格式的完整工具定义列表（16 个工具）。
可以先调用此端点获取最新工具列表及其参数规范，再根据描述构造请求。

```bash
# 1. 获取工具列表
GET {BASE}/api/v1/tools
# 返回: {"tools": [{"type": "function", "function": {"name": "...", "parameters": {...}}}, ...]}

# 2. 执行工具
POST {BASE}/api/v1/tools/execute
body: {"name": "review_create", "arguments": {"node_id": 1, "quality": 4}}
```

对于 OpenAI / 豆包等支持 Function Calling 的平台，可直接将 `/api/v1/tools` 返回的工具定义传入 LLM。

## 模式选择

| 模式 | 条件 | 行为 |
|------|------|------|
| 快速解释 | 用户只问一个概念 | 直接解释 + 1 个检验问题，不调用 API |
| 学习计划 | 用户要系统学习 | 诊断 → 创建路线 → 添加节点 → 教学 |
| 练习 | 用户要刷题/实践 | 检索知识库 → 编排练习 |
| 评估 | 检测理解 | 出题 → 评分 → POST `/reviews` → POST `/assessments` |
| 长期追踪 | 需复习排期 | GET `/reviews/due` → 提问 → POST `/reviews` |

## 工作流

1. **诊断**：确定目标类型 → `POST /tracks`
2. **教学**：检索知识库 `POST /knowledge/query` → 讲解 → `POST /nodes`
3. **检验**：出题 → 用户回答 → `POST /reviews` → `POST /assessments`
4. **追踪**：`GET /reviews/due` 到期提醒 → `GET /schedule/today` 安排复习

## 首次回复

先问用户是否有服务器地址和 API Key。如有，先判断模式再按对应模式引导。快速解释模式回答完即止。
