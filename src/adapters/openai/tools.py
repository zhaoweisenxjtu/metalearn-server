"""OpenAI Function Calling 格式工具定义。

为 OpenAI / 豆包 / 其他兼容 Function Calling 的平台提供工具描述。
"""

from engine.db import dao_user, dao_track, dao_node, dao_review, dao_assessment, dao_journal
from engine.core.sm2 import SM2Calculator
from engine.scheduler.multi_track import MultiTrackScheduler
from engine.core.indicators import Dashboard
from engine.core.fake_detection import FakeDetector
from engine.workflow.state_machine import get_guarded_next, is_valid_transition, get_state_label
from knowledge.retrieval import search as knowledge_search, sources as knowledge_sources, rebuild as knowledge_rebuild


def _tool(name: str, description: str, params: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": params["properties"],
                "required": params.get("required", []),
            },
        },
    }


def get_openai_tools() -> list[dict]:
    """返回 OpenAI Function Calling 格式的工具列表。

    Returns:
        list[dict]: OpenAI tools 定义，可直接传给 chat.completions.create(tools=...)
    """
    return [
        # ── User ──
        _tool("user_create", "创建新用户", {
            "properties": {
                "name": {"type": "string", "description": "用户名（唯一）"},
                "display_name": {"type": "string", "description": "显示名称"},
            },
            "required": ["name"],
        }),
        _tool("user_list", "列出所有用户", {
            "properties": {},
        }),
        _tool("user_delete", "删除用户", {
            "properties": {
                "user_id": {"type": "integer", "description": "用户 ID"},
            },
            "required": ["user_id"],
        }),

        # ── Track ──
        _tool("track_create", "创建新的学习路线", {
            "properties": {
                "user_id": {"type": "integer", "description": "用户 ID"},
                "name": {"type": "string", "description": "路线名称"},
                "type": {"type": "string", "enum": ["exam", "applied", "interest"]},
                "priority": {"type": "integer", "description": "优先级 1-5", "minimum": 1, "maximum": 5},
            },
            "required": ["user_id", "name"],
        }),
        _tool("track_list", "列出用户的学习路线", {
            "properties": {
                "user_id": {"type": "integer", "description": "用户 ID"},
            },
            "required": ["user_id"],
        }),
        _tool("track_update", "更新学习路线", {
            "properties": {
                "track_id": {"type": "integer"},
                "name": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "paused", "completed", "archived"]},
                "priority": {"type": "integer", "minimum": 1, "maximum": 5},
            },
            "required": ["track_id"],
        }),

        # ── Node ──
        _tool("node_add", "添加知识点到学习路线", {
            "properties": {
                "track_id": {"type": "integer"},
                "name": {"type": "string"},
                "importance": {"type": "integer", "minimum": 1, "maximum": 5},
                "level": {"type": "integer", "minimum": 1, "maximum": 5},
            },
            "required": ["track_id", "name"],
        }),
        _tool("node_list", "列出路线的知识点", {
            "properties": {
                "track_id": {"type": "integer"},
            },
            "required": ["track_id"],
        }),
        _tool("node_delete", "删除知识点", {
            "properties": {
                "node_id": {"type": "integer"},
            },
            "required": ["node_id"],
        }),

        # ── Review (SM-2) ──
        _tool("review_create", "执行 SM-2 间隔重复复习评分", {
            "properties": {
                "node_id": {"type": "integer"},
                "quality": {"type": "integer", "enum": [0, 1, 2, 3, 4, 5],
                            "description": "0=完全忘记 ~ 5=完美回忆"},
            },
            "required": ["node_id", "quality"],
        }),
        _tool("review_due", "查询今日到期待复习的知识点", {
            "properties": {
                "user_id": {"type": "integer"},
            },
            "required": ["user_id"],
        }),
        _tool("review_stats", "复习统计", {
            "properties": {
                "track_id": {"type": "integer"},
            },
            "required": ["track_id"],
        }),

        # ── Schedule ──
        _tool("schedule_today", "获取今日学习安排", {
            "properties": {
                "user_id": {"type": "integer"},
                "minutes": {"type": "integer", "description": "可用总时间（分钟）"},
            },
            "required": ["user_id"],
        }),

        # ── Knowledge ──
        _tool("knowledge_query", "检索知识库（认知科学方法、教学策略等）", {
            "properties": {
                "query": {"type": "string", "description": "查询内容"},
                "top_k": {"type": "integer", "description": "返回结果数"},
            },
            "required": ["query"],
        }),

        # ── Assessment ──
        _tool("assessment_log", "记录理解层级评估", {
            "properties": {
                "user_id": {"type": "integer"},
                "track_id": {"type": "integer"},
                "after": {"type": "integer", "description": "评估后层级 1-5", "minimum": 1, "maximum": 5},
                "node": {"type": "integer"},
                "duration": {"type": "integer"},
            },
            "required": ["user_id", "track_id", "after"],
        }),

        # ── Dashboard ──
        _tool("dashboard", "查看学习仪表盘（整体进度）", {
            "properties": {
                "user_id": {"type": "integer"},
            },
            "required": ["user_id"],
        }),
    ]


# Mapping from tool name to implementation function
TOOL_IMPLEMENTATIONS: dict[str, callable] = {
    "user_create": lambda **kw: dao_user.create_user(kw["name"], kw.get("display_name", kw["name"])),
    "user_list": lambda **_kw: dao_user.list_users(),
    "user_delete": lambda **kw: {"deleted": dao_user.delete_user(kw["user_id"])},
    "track_create": lambda **kw: dao_track.create_track(kw["user_id"], kw["name"], kw.get("type", "applied"), kw.get("priority", 3)),
    "track_list": lambda **kw: dao_track.list_tracks(kw.get("user_id")),
    "track_update": lambda **kw: dao_track.update_track(kw["track_id"], **{k: v for k, v in kw.items() if k != "track_id"}),
    "node_add": lambda **kw: dao_node.add_node(kw["track_id"], kw["name"], importance=kw.get("importance", 3), current_level=kw.get("level", 1)),
    "node_list": lambda **kw: dao_node.list_nodes(kw.get("track_id")),
    "node_delete": lambda **kw: {"deleted": dao_node.delete_node(kw["node_id"])},
    "review_create": lambda **kw: _execute_review(kw["node_id"], kw["quality"]),
    "review_due": lambda **kw: dao_node.get_due_nodes(user_id=kw.get("user_id")),
    "review_stats": lambda **kw: dao_review.get_review_stats(kw.get("track_id")),
    "schedule_today": lambda **kw: MultiTrackScheduler().get_schedule(kw["user_id"], total_minutes=kw.get("minutes")),
    "knowledge_query": lambda **kw: _execute_knowledge_query(kw["query"], kw.get("top_k", 5)),
    "assessment_log": lambda **kw: dao_assessment.log_assessment(kw["user_id"], kw["track_id"], kw["after"], kw.get("node"), duration_minutes=kw.get("duration", 0)),
    "dashboard": lambda **kw: Dashboard().overall(kw["user_id"]),
}


def _execute_review(node_id: int, quality: int) -> dict:
    node = dao_node.get_node(node_id)
    if not node:
        return {"error": f"Node {node_id} not found"}
    result = SM2Calculator.compute(quality, node["ef"], node["interval"], node["repetitions"])
    dao_node.update_node(node_id, ef=result["ef"], interval=result["interval_days"],
                         repetitions=result["repetitions"], next_review=result["next_review"])
    dao_review.create_review(node_id, quality, result["ef"], result["interval_days"])
    return {"node": node["name"], **result}


def _execute_knowledge_query(query: str, top_k: int = 5) -> list[dict]:
    return knowledge_search(query, top_k=top_k)


def execute_tool(name: str, arguments: dict) -> dict | list | str:
    """执行一个 OpenAI Function Calling 工具调用。

    Args:
        name: 工具名称
        arguments: 参数字典

    Returns:
        执行结果
    """
    func = TOOL_IMPLEMENTATIONS.get(name)
    if not func:
        return {"error": f"Unknown tool: {name}"}
    try:
        return func(**arguments)
    except Exception as e:
        return {"error": str(e)}
