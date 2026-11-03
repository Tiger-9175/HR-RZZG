"""SQLite persistence layer for evaluation records.

The system historically kept results only in the browser session, so nothing
survived a refresh. This module stores every evaluation plus its generated PDF
report so records can be listed, reviewed and re-downloaded later.

Only the standard library is used — no extra dependency, which keeps the
offline / intranet deployment story intact.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

DB_FILENAME = "evaluations.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluations (
    id                    TEXT PRIMARY KEY,
    created_at            TEXT NOT NULL,
    candidate_name        TEXT,
    department            TEXT,
    position              TEXT,
    applied_level         TEXT,
    profession            TEXT,
    standard_filename     TEXT,
    total_score           REAL,
    total_full_score      REAL,
    total_percentage      REAL,
    passed                INTEGER,
    responsibility_score  REAL,
    llm_model             TEXT,
    ppt_filename          TEXT,
    result_json           TEXT NOT NULL,
    ppt_content           TEXT,
    report_path           TEXT,
    report_created_at     TEXT,
    review_status         TEXT DEFAULT 'ai_reviewed',
    reviewer              TEXT DEFAULT '',
    review_comment        TEXT DEFAULT '',
    reviewed_at           TEXT
);
CREATE INDEX IF NOT EXISTS idx_evaluations_created ON evaluations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_evaluations_name ON evaluations(candidate_name);

CREATE TABLE IF NOT EXISTS batches (
    id                    TEXT PRIMARY KEY,
    created_at            TEXT NOT NULL,
    name                  TEXT DEFAULT '',
    candidate_level       TEXT DEFAULT '',
    responsibility_score  REAL DEFAULT 0,
    total                 INTEGER DEFAULT 0,
    finished              INTEGER DEFAULT 0,
    failed                INTEGER DEFAULT 0,
    status                TEXT DEFAULT 'running',
    message               TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS batch_items (
    id                    TEXT PRIMARY KEY,
    batch_id              TEXT NOT NULL,
    filename              TEXT DEFAULT '',
    candidate_name        TEXT DEFAULT '',
    status                TEXT DEFAULT 'pending',
    record_id             TEXT,
    message               TEXT DEFAULT '',
    updated_at            TEXT
);
CREATE INDEX IF NOT EXISTS idx_batch_items_batch ON batch_items(batch_id);
"""

# Columns added after the first release; applied on startup for old databases
MIGRATIONS = {
    "evaluations": {
        "review_status": "TEXT DEFAULT 'ai_reviewed'",
        "reviewer": "TEXT DEFAULT ''",
        "review_comment": "TEXT DEFAULT ''",
        "reviewed_at": "TEXT",
    },
}

SUMMARY_COLUMNS = (
    "id, created_at, candidate_name, department, position, applied_level, "
    "profession, standard_filename, total_score, total_full_score, "
    "total_percentage, passed, responsibility_score, llm_model, ppt_filename, "
    "report_path, report_created_at, review_status, reviewer, reviewed_at"
)

# 评审状态流转
REVIEW_STATUSES = ("ai_reviewed", "human_reviewed", "final_passed", "final_rejected")


def db_path() -> str:
    return os.path.join(settings.data_dir, DB_FILENAME)


def report_dir() -> str:
    path = os.path.join(settings.data_dir, "reports")
    os.makedirs(path, exist_ok=True)
    return path


@contextmanager
def _connect():
    conn = sqlite3.connect(db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the database file and schema if missing, then migrate."""
    os.makedirs(settings.data_dir, exist_ok=True)
    os.makedirs(report_dir(), exist_ok=True)
    with _connect() as conn:
        conn.executescript(SCHEMA)
        for table, columns in MIGRATIONS.items():
            existing = {row["name"] for row in
                        conn.execute(f"PRAGMA table_info({table})")}
            for column, ddl in columns.items():
                if column not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                    logger.info("Migrated %s: added column %s", table, column)
    logger.info("Evaluation database ready: %s", db_path())


def _row_to_summary(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["passed"] = bool(data.get("passed"))
    data["has_report"] = bool(data.get("report_path"))
    return data


def save_evaluation(
    result: dict,
    *,
    ppt_filename: str = "",
    ppt_content: str = "",
    standard_filename: str = "",
    responsibility_score: float = 0.0,
    llm_model: str = "",
    profession: str = "",
) -> str:
    """Persist one evaluation result, returning the new record id."""
    candidate = result.get("candidate") or {}
    record_id = uuid.uuid4().hex[:12]
    created_at = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """INSERT INTO evaluations (
                   id, created_at, candidate_name, department, position,
                   applied_level, profession, standard_filename, total_score,
                   total_full_score, total_percentage, passed,
                   responsibility_score, llm_model, ppt_filename, result_json,
                   ppt_content)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                record_id, created_at,
                candidate.get("name", ""), candidate.get("department", ""),
                candidate.get("position", ""), candidate.get("applied_level", ""),
                profession, standard_filename,
                float(result.get("total_score") or 0),
                float(result.get("total_full_score") or 0),
                float(result.get("total_percentage") or 0),
                1 if result.get("passed") else 0,
                float(responsibility_score or 0), llm_model, ppt_filename,
                json.dumps(result, ensure_ascii=False), ppt_content,
            ),
        )
    logger.info("Saved evaluation %s (%s)", record_id, candidate.get("name", ""))
    return record_id


def list_evaluations(
    keyword: str = "",
    profession: str = "",
    applied_level: str = "",
    passed: Optional[bool] = None,
    review_status: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    clauses, params = [], []
    if keyword:
        clauses.append("(candidate_name LIKE ? OR department LIKE ?)")
        params += [f"%{keyword}%", f"%{keyword}%"]
    if profession:
        clauses.append("profession = ?")
        params.append(profession)
    if applied_level:
        clauses.append("applied_level = ?")
        params.append(applied_level)
    if passed is not None:
        clauses.append("passed = ?")
        params.append(1 if passed else 0)
    if review_status:
        clauses.append("review_status = ?")
        params.append(review_status)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    page = max(1, int(page or 1))
    page_size = min(100, max(1, int(page_size or 20)))
    offset = (page - 1) * page_size

    with _connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM evaluations {where}",
                             params).fetchone()[0]
        rows = conn.execute(
            f"SELECT {SUMMARY_COLUMNS} FROM evaluations {where} "
            f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_row_to_summary(r) for r in rows],
    }


def get_evaluation(record_id: str, with_content: bool = True) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM evaluations WHERE id = ?",
                           (record_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    data["passed"] = bool(data.get("passed"))
    data["result"] = json.loads(data.pop("result_json"))
    data["has_report"] = bool(data.get("report_path"))
    if not with_content:
        data.pop("ppt_content", None)
    return data


def delete_evaluation(record_id: str) -> bool:
    record = get_evaluation(record_id, with_content=False)
    if not record:
        return False
    path = record.get("report_path")
    with _connect() as conn:
        conn.execute("DELETE FROM evaluations WHERE id = ?", (record_id,))
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError as exc:  # pragma: no cover - fs specific
            logger.warning("Failed to remove report file %s: %s", path, exc)
    logger.info("Deleted evaluation %s", record_id)
    return True


def set_report(record_id: str, report_path: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE evaluations SET report_path = ?, report_created_at = ? "
            "WHERE id = ?",
            (report_path, datetime.now().isoformat(timespec="seconds"), record_id),
        )


def report_file_path(record_id: str) -> str:
    return os.path.join(report_dir(), f"{record_id}.pdf")


def update_review(record_id: str, status: str, reviewer: str = "",
                  comment: str = "") -> bool:
    """Advance the review workflow of one record."""
    if status not in REVIEW_STATUSES:
        raise ValueError(f"未知评审状态: {status}")
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE evaluations SET review_status = ?, reviewer = ?, "
            "review_comment = ?, reviewed_at = ? WHERE id = ?",
            (status, reviewer, comment,
             datetime.now().isoformat(timespec="seconds"), record_id),
        )
        return cursor.rowcount > 0


def stats_overview() -> dict:
    with _connect() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS total,
                      SUM(passed) AS passed,
                      AVG(total_percentage) AS avg_percentage,
                      SUM(CASE WHEN report_path IS NOT NULL THEN 1 ELSE 0 END) AS reports
               FROM evaluations"""
        ).fetchone()
        by_profession = conn.execute(
            """SELECT profession, COUNT(*) AS count, AVG(total_percentage) AS avg
               FROM evaluations WHERE profession <> ''
               GROUP BY profession ORDER BY count DESC"""
        ).fetchall()
        by_review = conn.execute(
            """SELECT review_status, COUNT(*) AS count FROM evaluations
               GROUP BY review_status"""
        ).fetchall()
        recent = conn.execute(
            f"SELECT {SUMMARY_COLUMNS} FROM evaluations "
            "ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
    total = row["total"] or 0
    return {
        "total": total,
        "passed": row["passed"] or 0,
        "pass_rate": round((row["passed"] or 0) / total * 100, 1) if total else 0,
        "avg_percentage": round(row["avg_percentage"] or 0, 1),
        "reports": row["reports"] or 0,
        "by_profession": [dict(r) for r in by_profession],
        "by_review_status": {r["review_status"] or "ai_reviewed": r["count"]
                             for r in by_review},
        "recent": [_row_to_summary(r) for r in recent],
    }


# ------------------------------------------------------------- comparison ----
def compare_records(ids: list[str]) -> dict:
    """Build a dimension-aligned comparison dataset for several records."""
    records = []
    for record_id in ids:
        record = get_evaluation(record_id, with_content=False)
        if record:
            records.append(record)

    dimension_order: list[str] = []
    full_scores: dict[str, float] = {}
    for record in records:
        for dim in record["result"].get("dimensions") or []:
            name = (dim.get("name") or "").strip()
            if not name:
                continue
            if name not in dimension_order:
                dimension_order.append(name)
            full = float(dim.get("full_score") or 0)
            full_scores[name] = max(full_scores.get(name, 0), full)

    items = []
    for record in records:
        result = record["result"]
        scores = {(d.get("name") or "").strip(): d.get("score")
                  for d in result.get("dimensions") or []}
        candidate = result.get("candidate") or {}
        items.append({
            "id": record["id"],
            "name": candidate.get("name") or record.get("candidate_name") or "",
            "department": candidate.get("department") or record.get("department"),
            "profession": record.get("profession"),
            "applied_level": candidate.get("applied_level") or record.get("applied_level"),
            "review_status": record.get("review_status"),
            "total_score": record.get("total_score"),
            "total_full_score": record.get("total_full_score"),
            "total_percentage": record.get("total_percentage"),
            "passed": record.get("passed"),
            "dimensions": [
                {
                    "name": name,
                    "score": scores.get(name),
                    "full_score": full_scores.get(name, 0),
                    "percentage": round((scores.get(name) or 0)
                                        / full_scores[name] * 100, 1)
                    if full_scores.get(name) else 0,
                }
                for name in dimension_order
            ],
        })

    return {
        "dimensions": [{"name": n, "full_score": full_scores.get(n, 0)}
                       for n in dimension_order],
        "records": items,
        "count": len(items),
    }


# ----------------------------------------------------------------- batches ----
def create_batch(name: str, candidate_level: str, responsibility_score: float,
                 filenames: list[str]) -> dict:
    """Create a batch job with one pending item per candidate file."""
    batch_id = uuid.uuid4().hex[:12]
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            "INSERT INTO batches (id, created_at, name, candidate_level, "
            "responsibility_score, total, finished, failed, status) "
            "VALUES (?,?,?,?,?,?,0,0,'running')",
            (batch_id, now, name, candidate_level, responsibility_score,
             len(filenames)),
        )
        for filename in filenames:
            conn.execute(
                "INSERT INTO batch_items (id, batch_id, filename, status, updated_at) "
                "VALUES (?,?,?,'pending',?)",
                (uuid.uuid4().hex[:12], batch_id, filename, now),
            )
    logger.info("Created batch %s with %d items", batch_id, len(filenames))
    return get_batch(batch_id)


def _batch_row(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["progress"] = round((data["finished"] + data["failed"])
                             / data["total"] * 100, 1) if data["total"] else 0
    return data


def get_batch(batch_id: str) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM batches WHERE id = ?",
                           (batch_id,)).fetchone()
        if not row:
            return None
        items = conn.execute(
            "SELECT bi.id, bi.filename, bi.candidate_name, bi.status, "
            "bi.record_id, bi.message, bi.updated_at, "
            "e.total_score, e.total_percentage, e.passed "
            "FROM batch_items bi LEFT JOIN evaluations e ON e.id = bi.record_id "
            "WHERE bi.batch_id = ? ORDER BY bi.rowid",
            (batch_id,),
        ).fetchall()
    batch = _batch_row(row)
    batch["items"] = []
    for item in items:
        data = dict(item)
        if data.get("passed") is not None:
            data["passed"] = bool(data["passed"])
        batch["items"].append(data)
    return batch


def list_batches(limit: int = 30) -> dict:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM batches ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return {"items": [_batch_row(r) for r in rows], "total": len(rows)}


def pending_batch_items(batch_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, filename FROM batch_items "
            "WHERE batch_id = ? AND status = 'pending' ORDER BY rowid",
            (batch_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def set_batch_item(item_id: str, status: str, record_id: Optional[str] = None,
                   message: str = "", candidate_name: Optional[str] = None) -> None:
    fields = ["status = ?", "updated_at = ?"]
    values: list[Any] = [status, datetime.now().isoformat(timespec="seconds")]
    if record_id is not None:
        fields.append("record_id = ?")
        values.append(record_id)
    if message:
        fields.append("message = ?")
        values.append(message[:500])
    if candidate_name is not None:
        fields.append("candidate_name = ?")
        values.append(candidate_name)
    values.append(item_id)
    with _connect() as conn:
        conn.execute(f"UPDATE batch_items SET {', '.join(fields)} WHERE id = ?",
                     values)


def refresh_batch(batch_id: str, status: Optional[str] = None) -> None:
    with _connect() as conn:
        counts = conn.execute(
            "SELECT SUM(status = 'success') AS ok, SUM(status = 'failed') AS bad "
            "FROM batch_items WHERE batch_id = ?", (batch_id,)
        ).fetchone()
        finished, failed = counts["ok"] or 0, counts["bad"] or 0
        if status:
            conn.execute(
                "UPDATE batches SET finished = ?, failed = ?, status = ? WHERE id = ?",
                (finished, failed, status, batch_id))
        else:
            conn.execute(
                "UPDATE batches SET finished = ?, failed = ? WHERE id = ?",
                (finished, failed, batch_id))


def batch_status(batch_id: str) -> str:
    with _connect() as conn:
        row = conn.execute("SELECT status FROM batches WHERE id = ?",
                           (batch_id,)).fetchone()
    return row["status"] if row else ""

def cancel_batch(batch_id: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE batches SET status = 'cancelled', message = '用户已取消' "
            "WHERE id = ? AND status = 'running'", (batch_id,))
        conn.execute(
            "UPDATE batch_items SET status = 'cancelled' "
            "WHERE batch_id = ? AND status = 'pending'", (batch_id,))
        return cursor.rowcount > 0


def delete_batch(batch_id: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM batches WHERE id = ?", (batch_id,))
        conn.execute("DELETE FROM batch_items WHERE batch_id = ?", (batch_id,))
        return cursor.rowcount > 0
