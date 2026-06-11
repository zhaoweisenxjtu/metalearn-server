"""Knowledge Node DAO: CRUD for knowledge_nodes table."""

from datetime import date, timedelta
from .database import get_connection, row_to_dict, rows_to_dicts


def add_node(track_id: int, name: str, description: str = "",
             parent_id: int | None = None, importance: int = 3,
             current_level: int = 1) -> dict:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO knowledge_nodes (track_id, parent_id, name, description, importance, current_level) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (track_id, parent_id, name, description, importance, current_level),
        )
        conn.commit()
        return get_node(cur.lastrowid)
    finally:
        conn.close()


def get_node(node_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ?", (node_id,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def list_nodes(track_id: int | None = None, status: str | None = None) -> list[dict]:
    conn = get_connection()
    try:
        query = "SELECT * FROM knowledge_nodes"
        params = []
        conditions = []
        if track_id is not None:
            conditions.append("track_id = ?")
            params.append(track_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY importance DESC, created_at"
        rows = conn.execute(query, params).fetchall()
        return rows_to_dicts(rows)
    finally:
        conn.close()


def update_node(node_id: int, **kwargs) -> dict | None:
    allowed = {"name", "description", "importance", "current_level", "status",
               "ef", "interval", "repetitions", "next_review", "parent_id"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return get_node(node_id)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    set_clause += ", updated_at = date('now')"
    values = list(updates.values())

    conn = get_connection()
    try:
        conn.execute(f"UPDATE knowledge_nodes SET {set_clause} WHERE id = ?", (*values, node_id))
        conn.commit()
        return get_node(node_id)
    finally:
        conn.close()


def delete_node(node_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM knowledge_nodes WHERE id = ?", (node_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_due_nodes(track_id: int | None = None, user_id: int | None = None) -> list[dict]:
    """Get nodes where next_review <= today."""
    today = date.today().isoformat()
    conn = get_connection()
    try:
        if track_id:
            rows = conn.execute(
                "SELECT n.* FROM knowledge_nodes n "
                "WHERE n.track_id = ? AND n.next_review IS NOT NULL AND n.next_review <= ? "
                "AND n.status = 'active' ORDER BY n.next_review",
                (track_id, today),
            ).fetchall()
        elif user_id:
            rows = conn.execute(
                "SELECT n.* FROM knowledge_nodes n "
                "JOIN tracks t ON n.track_id = t.id "
                "WHERE t.user_id = ? AND n.next_review IS NOT NULL AND n.next_review <= ? "
                "AND n.status = 'active' AND t.status = 'active' "
                "ORDER BY n.next_review",
                (user_id, today),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT n.* FROM knowledge_nodes n "
                "WHERE n.next_review IS NOT NULL AND n.next_review <= ? "
                "AND n.status = 'active' ORDER BY n.next_review",
                (today,),
            ).fetchall()
        return rows_to_dicts(rows)
    finally:
        conn.close()


def add_dependency(node_id: int, depends_on_id: int, relation_type: str = "prerequisite") -> bool:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO node_dependencies (node_id, depends_on_id, relation_type) "
            "VALUES (?, ?, ?)",
            (node_id, depends_on_id, relation_type),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_dependencies(node_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT d.*, n.name as depends_on_name FROM node_dependencies d "
            "JOIN knowledge_nodes n ON d.depends_on_id = n.id "
            "WHERE d.node_id = ?",
            (node_id,),
        ).fetchall()
        return rows_to_dicts(rows)
    finally:
        conn.close()
