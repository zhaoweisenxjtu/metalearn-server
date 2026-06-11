#!/usr/bin/env python3
"""Meta-Learning Engine CLI

Usage:
    meta-learn user create <name>
    meta-learn track create <uid> <name> -t <exam|applied|interest>
    meta-learn node add <tid> <name> -i <1-5>
    meta-learn review create <nid> -q <0-5>
    meta-learn workflow get-next <tid>
    meta-learn schedule today --user <uid>
    meta-learn report dashboard <uid>
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from engine.db.database import init_db, get_connection
from engine.db import dao_user, dao_track, dao_node, dao_review, dao_assessment, dao_journal
from engine.db.migrate_from_json import JsonMigrator
from engine.core.sm2 import SM2Calculator
from engine.core.fake_detection import FakeDetector
from engine.core.indicators import Dashboard
from engine.workflow.state_machine import (
    get_next_recommended, get_guarded_next, is_valid_transition,
    get_allowed_transitions, get_state_label,
)
from engine.scheduler.multi_track import MultiTrackScheduler


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(0)


def md(text: str):
    print(text)


# ── User ─────────────────────────────────────────────

def cmd_user_create(args):
    user = dao_user.create_user(args.name, args.display_name or args.name)
    if args.json: print_json(user)
    md(f"用户创建成功: **{user['name']}** (ID: {user['id']})")


def cmd_user_list(args):
    users = dao_user.list_users()
    if args.json: print_json(users)
    if not users: md("暂无用户。"); return
    lines = ["## 用户列表\n", "| ID | 名称 | 路线数 | 创建时间 |", "|----|------|--------|---------|"]
    conn = get_connection()
    for u in users:
        cnt = conn.execute("SELECT COUNT(*) AS c FROM tracks WHERE user_id=?", (u["id"],)).fetchone()["c"]
        lines.append(f"| {u['id']} | {u['name']} | {cnt} | {u['created_at']} |")
    conn.close()
    md("\n".join(lines))


def cmd_user_delete(args):
    ok = dao_user.delete_user(args.user_id)
    if args.json: print_json({"deleted": ok})
    md(f"用户 {'已删除' if ok else '未找到'}.")


# ── Track ────────────────────────────────────────────

def cmd_track_create(args):
    track = dao_track.create_track(args.user_id, args.name, args.type, args.priority)
    if args.json: print_json(track)
    md(f"路线创建成功: **{track['name']}** (ID: {track['id']}, 类型: {track['target_type']})")


def cmd_track_list(args):
    tracks = dao_track.list_tracks(args.user_id, args.status)
    if args.json: print_json(tracks)
    if not tracks: md("暂无学习路线。"); return
    lines = ["## 学习路线\n", "| ID | 名称 | 类型 | 状态 | 优先级 | 进度 | 创建时间 |", "|----|------|------|------|--------|------|---------|"]
    for t in tracks:
        lines.append(f"| {t['id']} | {t['name']} | {t['target_type']} | {t['status']} | {t['priority']} | {get_state_label(t['current_state'])} | {t['created_at']} |")
    md("\n".join(lines))


def cmd_track_update(args):
    updates = {}
    if args.name: updates["name"] = args.name
    if args.status: updates["status"] = args.status
    if args.priority is not None: updates["priority"] = args.priority
    track = dao_track.update_track(args.track_id, **updates)
    if args.json: print_json(track)
    md(f"路线已更新: **{track['name']}** (ID: {track['id']})")


# ── Node ─────────────────────────────────────────────

def cmd_node_add(args):
    node = dao_node.add_node(args.track_id, args.name, args.description, args.parent, args.importance, args.level)
    if args.json: print_json(node)
    md(f"节点已添加: **{node['name']}** (ID: {node['id']}, L{node['current_level']})")


def cmd_node_list(args):
    nodes = dao_node.list_nodes(args.track_id, args.status)
    if args.json: print_json(nodes)
    if not nodes: md("暂无知识节点。"); return
    lines = ["## 知识节点\n", "| ID | 名称 | 层级 | 重要度 | 状态 | 下次复习 |", "|----|------|------|--------|------|---------|"]
    today = date.today().isoformat()
    for n in nodes:
        r = n["next_review"] or "-"
        if n["next_review"] and n["next_review"] <= today: r = f"**{n['next_review']}** (逾期)"
        lines.append(f"| {n['id']} | {n['name']} | L{n['current_level']} | {n['importance']} | {n['status']} | {r} |")
    md("\n".join(lines))


def cmd_node_update(args):
    updates = {}
    if args.name: updates["name"] = args.name
    if args.level is not None: updates["current_level"] = args.level
    if args.status: updates["status"] = args.status
    node = dao_node.update_node(args.node_id, **updates)
    if args.json: print_json(node)
    md(f"节点已更新: **{node['name']}** (L{node['current_level']})")


def cmd_node_delete(args):
    ok = dao_node.delete_node(args.node_id)
    if args.json: print_json({"deleted": ok})
    md(f"节点 {'已删除' if ok else '未找到'}.")


# ── Review ───────────────────────────────────────────

def cmd_review_create(args):
    node = dao_node.get_node(args.node_id)
    if not node: md(f"错误: 节点 {args.node_id} 不存在。"); sys.exit(1)
    result = SM2Calculator.compute(args.quality, node["ef"], node["interval"], node["repetitions"])
    dao_node.update_node(args.node_id, ef=result["ef"], interval=result["interval_days"],
                         repetitions=result["repetitions"], next_review=result["next_review"])
    review = dao_review.create_review(args.node_id, args.quality, result["ef"], result["interval_days"])
    if args.json: print_json({"node": node["name"], **result, "review_id": review["id"]})
    qmap = {0: "完全忘记", 1: "困难", 2: "勉强", 3: "一般", 4: "良好", 5: "完美"}
    md(f"复习完成: **{node['name']}**\n- 评分: {args.quality}/5 ({qmap.get(args.quality)})\n- EF: {node['ef']}→{result['ef']}\n- 间隔: {result['interval_days']}天\n- 下次复习: {result['next_review']}")


def cmd_review_due(args):
    due = dao_node.get_due_nodes(args.track_id, args.user_id)
    if args.json: print_json(due)
    if not due: md("今日无到期复习！"); return
    lines = ["## 今日待复习\n", "| ID | 节点名称 | 路线 | 上次间隔 | 重要度 |", "|----|---------|------|---------|--------|"]
    conn = get_connection()
    for n in due:
        t = conn.execute("SELECT name FROM tracks WHERE id=?", (n["track_id"],)).fetchone()
        lines.append(f"| {n['id']} | {n['name']} | {t['name'] if t else '?'} | {n['interval']}天 | {n['importance']} |")
    conn.close()
    md("\n".join(lines) + f"\n共 **{len(due)}** 项待复习。")


def cmd_review_stats(args):
    stats = dao_review.get_review_stats(args.track_id)
    if args.json: print_json(stats)
    md(f"## 复习统计\n- 总复习次数: {stats['total_reviews']}\n- 平均评分: {stats['avg_quality']}/5\n- 平均 EF: {stats['avg_ef']}\n- 通过率: {stats['pass_rate']*100 if stats['pass_rate'] else 0:.1f}%")


# ── Assessment ───────────────────────────────────────

def cmd_assessment_log(args):
    a = dao_assessment.log_assessment(args.user_id, args.track_id, args.after, args.node, args.before, args.methods, args.duration, args.notes)
    if args.json: print_json(a)
    md(f"评估记录已保存 (ID: {a['id']})")


def cmd_assessment_list(args):
    items = dao_assessment.list_assessments(args.track_id, args.user_id)
    if args.json: print_json(items)
    if not items: md("暂无评估记录。"); return
    lines = ["## 评估记录\n", "| ID | 日期 | 节点 | L前→L后 | 用时 | 方法 |", "|----|------|------|---------|------|------|"]
    for a in items:
        node_name = ""
        if a["node_id"]:
            n = dao_node.get_node(a["node_id"])
            node_name = n["name"] if n else f"#{a['node_id']}"
        ms = ", ".join(json.loads(a["methods"])) if a["methods"] != "[]" else "-"
        lines.append(f"| {a['id']} | {a['created_at'][:10]} | {node_name} | L{a['level_before']}→L{a['level_after']} | {a['duration_minutes']}min | {ms} |")
    md("\n".join(lines))


# ── Journal ──────────────────────────────────────────

def cmd_journal_create(args):
    e = dao_journal.create_journal(args.user_id, args.date, focus_minutes=args.focus, diffuse_minutes=args.diffuse, topics=args.topics, methods=args.methods, highlights=args.highlights, struggles=args.struggles, tomorrow_plan=args.tomorrow)
    if args.json: print_json(e)
    md(f"学习日志已保存 ({e['date']})")


def cmd_journal_get(args):
    e = dao_journal.get_journal_by_date(args.user_id, args.date)
    if args.json: print_json(e)
    if not e: md(f"{args.date} 无学习日志。"); return
    topics = ", ".join(json.loads(e["topics"])) if e["topics"] != "[]" else "-"
    methods = ", ".join(json.loads(e["methods"])) if e["methods"] != "[]" else "-"
    md(f"## 学习日志 — {e['date']}\n- 专注: {e['focus_minutes']}min | 发散: {e['diffuse_minutes']}min\n- 内容: {topics}\n- 方法: {methods}\n- 亮点: {e['highlights'] or '-'}\n- 卡点: {e['struggles'] or '-'}\n- 明日计划: {e['tomorrow_plan'] or '-'}")


# ── Workflow ─────────────────────────────────────────

def cmd_workflow_status(args):
    t = dao_track.get_track(args.track_id)
    if args.json: print_json(t)
    if not t: md(f"错误: 路线 {args.track_id} 不存在。"); return
    md(f"## 工作流状态 — {t['name']}\n- 当前阶段: **{get_state_label(t['current_state'])}**\n- 可转换: {', '.join(get_state_label(s) for s in get_allowed_transitions(t['current_state'])) or '无（已终态）'}\n- 目标类型: {t['target_type']}\n- 状态: {t['status']}")


def cmd_workflow_get_next(args):
    t = dao_track.get_track(args.track_id)
    if not t: md(f"错误: 路线 {args.track_id} 不存在。"); sys.exit(1)
    result = get_guarded_next(t, dao_node.list_nodes(args.track_id))
    if args.json: print_json(result)
    md(f"推荐下一步: **{get_state_label(result['next_state'])}**\n理由: {result['reason']}")


def cmd_workflow_transition(args):
    t = dao_track.get_track(args.track_id)
    if not t: md(f"错误: 路线 {args.track_id} 不存在。"); sys.exit(1)
    if not is_valid_transition(t["current_state"], args.to):
        md(f"错误: 不能从 `{t['current_state']}` 转换到 `{args.to}`。允许: {', '.join(get_allowed_transitions(t['current_state']))}")
        sys.exit(1)
    t = dao_track.update_track(args.track_id, current_state=args.to)
    if args.json: print_json(t)
    md(f"状态已转换: **{get_state_label(args.to)}**")


# ── Schedule ─────────────────────────────────────────

def cmd_schedule_today(args):
    s = MultiTrackScheduler().get_schedule(args.user_id, args.minutes)
    if args.json: print_json(s)
    if not s.get("tracks"): md(s.get("message", "暂无安排。")); return
    lines = [f"## 今日学习安排 — {s['date']}\n总可用时间: **{s['total_minutes']} 分钟**\n", "| 路线 | 优先级 | 急迫度 | 分配时间 | 复习 | 新学 | 活动 |", "|------|--------|--------|---------|------|------|------|"]
    for t in s["tracks"]:
        acts = "; ".join(f"{a['type']}({'记' if a['type']=='review' else '学'}{a['count']})" for a in t["activities"])
        lines.append(f"| {t['name']} | {t['priority']} | {t['urgency']:.2f} | {t['allocation_minutes']}min | {t['due_reviews']} | {t['pending_nodes']} | {acts} |")
    md("\n".join(lines))


def cmd_schedule_optimize(args):
    args.minutes = args.total_minutes
    cmd_schedule_today(args)


# ── Report ───────────────────────────────────────────

def cmd_report_dashboard(args):
    d = Dashboard().overall(args.user_id)
    if args.json: print_json(d)
    md(f"## 学习仪表盘\n\n```\n[知识总量]  {d['total_nodes']} 个节点\n[L3+ 占比]  {d['l3_plus_pct']}%\n[按时复习]  {d['ontime_review_pct']}%\n[月跃迁]    {d['monthly_jumps']} 次\n[平均 EF]   {d['avg_ef']}\n```")


def cmd_report_track(args):
    d = Dashboard().track_summary(args.track_id)
    if args.json: print_json(d)
    if "error" in d: md(f"错误: {d['error']}"); return
    lv = ", ".join(f"L{k}: {v}" for k, v in d["level_distribution"].items())
    md(f"## 路线报告 — {d['track_name']}\n- 类型: {d['target_type']} | 阶段: {get_state_label(d['current_state'])}\n- 总节点: {d['total_nodes']} | 活跃: {d['active_nodes']} | 已掌握(L3+): {d['mastered_nodes']}\n- 平均层级: {d['avg_level']:.1f}\n- 待复习: {d['due_reviews']} 项\n- 层级分布: {lv or '暂无节点'}")


def cmd_report_migration(args):
    r = JsonMigrator().report()
    if args.json: print_json(r)
    lines = ["## JSON 迁移报告\n"]
    if r["json_files_found"]:
        lines.append("找到以下 JSON 文件:")
        for f in r["json_files_found"]: lines.append(f"- [found] {f}")
        lines.append(f"\n预估可迁移节点数: {r['estimated_nodes']}\n执行迁移: `meta-learn report migration --execute`")
    else: lines.append("未找到旧版 JSON 数据文件。")
    for f in r["json_files_missing"]: lines.append(f"- [missing] {f}")
    md("\n".join(lines))


def cmd_report_migration_exec(args):
    s = JsonMigrator().migrate(args.user, args.track)
    if args.json: print_json(s)
    lines = [f"## 迁移完成\n- 用户 ID: {s.get('user_id', '-')}\n- 路线 ID: {s.get('track_id', '-')}\n- 迁移节点: {s['nodes']}\n- 迁移复习记录: {s['reviews']}\n- 迁移评估记录: {s['assessments']}\n- 迁移学习日志: {s['journals']}"]
    if s["errors"]:
        lines.append("\n错误:")
        for e in s["errors"]: lines.append(f"- [warn] {e}")
    md("\n".join(lines))


# ── Knowledge ────────────────────────────────────────

def cmd_knowledge_query(args):
    from knowledge.retrieval import search
    results = search(args.query, args.top_k, args.scope)
    if args.json: print_json(results)
    if not results: md("知识库未找到相关内容。"); return
    lines = ["## 知识检索结果\n", f"查询: _{args.query}_\n", "| 来源 | 章节 | 类别 | 得分 | 内容摘要 |", "|------|------|------|------|---------|"]
    for r in results:
        content = r["content"][:80].replace("\n", " ")
        lines.append(f"| {r['source']} | {r['section']} | {r['category']} | {r.get('score', '-')} | {content}... |")
    md("\n".join(lines))


def cmd_knowledge_sources(args):
    from knowledge.retrieval import sources
    srcs = sources()
    if args.json: print_json(srcs)
    if not srcs: md("暂无知识源。"); return
    lines = ["## 知识源\n", "| 文件 | 类别 | Chunk 数 |", "|------|------|---------|"]
    for s in srcs:
        lines.append(f"| {s['source']} | {s['category']} | {s['chunks']} |")
    md("\n".join(lines))


def cmd_knowledge_reindex(args):
    from knowledge.retrieval import rebuild
    count = rebuild()
    if args.json: print_json({"chunks": count})
    md(f"知识库索引重建完成，共 **{count}** 个 Chunk。")


# ── Argparse ─────────────────────────────────────────

def main():
    # Allow --json anywhere in the command line
    json_mode = "--json" in sys.argv
    argv = [a for a in sys.argv[1:] if a != "--json"]

    parser = argparse.ArgumentParser(description="元学习引擎 CLI")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    sub = parser.add_subparsers(dest="command")

    p_user = sub.add_parser("user")
    pu = p_user.add_subparsers(dest="subcommand")
    p = pu.add_parser("create"); p.add_argument("name"); p.add_argument("--display-name"); p.set_defaults(func=cmd_user_create)
    p = pu.add_parser("list"); p.set_defaults(func=cmd_user_list)
    p = pu.add_parser("delete"); p.add_argument("user_id", type=int); p.set_defaults(func=cmd_user_delete)

    p_track = sub.add_parser("track")
    pt = p_track.add_subparsers(dest="subcommand")
    p = pt.add_parser("create"); p.add_argument("user_id", type=int); p.add_argument("name")
    p.add_argument("--type", "-t", choices=["exam", "applied", "interest"], default="applied")
    p.add_argument("--priority", "-p", type=int, default=3, choices=range(1, 6))
    p.set_defaults(func=cmd_track_create)
    p = pt.add_parser("list"); p.add_argument("user_id", type=int); p.add_argument("--status"); p.set_defaults(func=cmd_track_list)
    p = pt.add_parser("update"); p.add_argument("track_id", type=int); p.add_argument("--name"); p.add_argument("--status"); p.add_argument("--priority", type=int); p.set_defaults(func=cmd_track_update)

    p_node = sub.add_parser("node")
    pn = p_node.add_subparsers(dest="subcommand")
    p = pn.add_parser("add"); p.add_argument("track_id", type=int); p.add_argument("name")
    p.add_argument("--description", "-d", default=""); p.add_argument("--parent", type=int)
    p.add_argument("--importance", "-i", type=int, default=3, choices=range(1, 6))
    p.add_argument("--level", "-l", type=int, default=1, choices=range(1, 6))
    p.set_defaults(func=cmd_node_add)
    p = pn.add_parser("list"); p.add_argument("track_id", type=int); p.add_argument("--status"); p.set_defaults(func=cmd_node_list)
    p = pn.add_parser("update"); p.add_argument("node_id", type=int); p.add_argument("--name"); p.add_argument("--level", type=int); p.add_argument("--status"); p.set_defaults(func=cmd_node_update)
    p = pn.add_parser("delete"); p.add_argument("node_id", type=int); p.set_defaults(func=cmd_node_delete)

    p_review = sub.add_parser("review")
    pr = p_review.add_subparsers(dest="subcommand")
    p = pr.add_parser("create"); p.add_argument("node_id", type=int); p.add_argument("--quality", "-q", type=int, required=True, choices=range(0, 6)); p.set_defaults(func=cmd_review_create)
    p = pr.add_parser("due"); p.add_argument("--track", dest="track_id", type=int); p.add_argument("--user", dest="user_id", type=int); p.set_defaults(func=cmd_review_due)
    p = pr.add_parser("stats"); p.add_argument("--track", dest="track_id", type=int); p.set_defaults(func=cmd_review_stats)

    p_assess = sub.add_parser("assessment")
    pa = p_assess.add_subparsers(dest="subcommand")
    p = pa.add_parser("log"); p.add_argument("user_id", type=int); p.add_argument("track_id", type=int)
    p.add_argument("--after", type=int, required=True, choices=range(1, 6))
    p.add_argument("--before", type=int, choices=range(1, 6)); p.add_argument("--node", type=int)
    p.add_argument("--methods", type=json.loads, default=[]); p.add_argument("--duration", type=int, default=0); p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_assessment_log)
    p = pa.add_parser("list"); p.add_argument("--track", dest="track_id", type=int); p.add_argument("--user", dest="user_id", type=int); p.set_defaults(func=cmd_assessment_list)

    p_journal = sub.add_parser("journal")
    pj = p_journal.add_subparsers(dest="subcommand")
    p = pj.add_parser("create"); p.add_argument("user_id", type=int)
    p.add_argument("--date", default=date.today().isoformat()); p.add_argument("--focus", type=int, default=0); p.add_argument("--diffuse", type=int, default=0)
    p.add_argument("--topics", type=json.loads, default=[]); p.add_argument("--methods", type=json.loads, default=[])
    p.add_argument("--highlights", default=""); p.add_argument("--struggles", default=""); p.add_argument("--tomorrow", default="")
    p.set_defaults(func=cmd_journal_create)
    p = pj.add_parser("get"); p.add_argument("user_id", type=int); p.add_argument("--date", default=date.today().isoformat()); p.set_defaults(func=cmd_journal_get)

    p_wf = sub.add_parser("workflow")
    pw = p_wf.add_subparsers(dest="subcommand")
    p = pw.add_parser("status"); p.add_argument("track_id", type=int); p.set_defaults(func=cmd_workflow_status)
    p = pw.add_parser("get-next"); p.add_argument("track_id", type=int); p.set_defaults(func=cmd_workflow_get_next)
    p = pw.add_parser("transition"); p.add_argument("track_id", type=int); p.add_argument("--to", required=True); p.set_defaults(func=cmd_workflow_transition)

    p_sched = sub.add_parser("schedule")
    ps = p_sched.add_subparsers(dest="subcommand")
    p = ps.add_parser("today"); p.add_argument("--user", dest="user_id", type=int, required=True); p.add_argument("--minutes", type=int); p.set_defaults(func=cmd_schedule_today)
    p = ps.add_parser("optimize"); p.add_argument("user_id", type=int); p.add_argument("--total-minutes", type=int, required=True); p.set_defaults(func=cmd_schedule_optimize)

    p_report = sub.add_parser("report")
    prp = p_report.add_subparsers(dest="subcommand")
    p = prp.add_parser("dashboard"); p.add_argument("user_id", type=int); p.set_defaults(func=cmd_report_dashboard)
    p = prp.add_parser("track"); p.add_argument("track_id", type=int); p.set_defaults(func=cmd_report_track)
    p = prp.add_parser("migration"); p.set_defaults(func=cmd_report_migration)
    p = prp.add_parser("migrate"); p.add_argument("--user", default="default_user"); p.add_argument("--track", default="默认学习路线"); p.set_defaults(func=cmd_report_migration_exec)

    p_knowledge = sub.add_parser("knowledge")
    pk = p_knowledge.add_subparsers(dest="subcommand")
    p = pk.add_parser("query"); p.add_argument("query"); p.add_argument("--top-k", type=int, default=5); p.add_argument("--scope"); p.set_defaults(func=cmd_knowledge_query)
    p = pk.add_parser("sources"); p.set_defaults(func=cmd_knowledge_sources)
    p = pk.add_parser("reindex"); p.set_defaults(func=cmd_knowledge_reindex)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help(); sys.exit(1)

    args.json = json_mode
    init_db()
    args.func(args)


if __name__ == "__main__":
    main()
