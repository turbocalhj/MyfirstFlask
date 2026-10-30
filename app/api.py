"""JSON API 蓝图：和 HTML 页面共用同一套数据与路由机制。

学习点 13：Flask 天生适合写 API——
  - jsonify() 自动序列化并设置 Content-Type: application/json
  - request.get_json() 解析请求体
  - 用返回的 (数据, 状态码) 元组直接控制 HTTP 状态
"""
from flask import Blueprint, abort, g, jsonify, request

from .db import get_db

bp = Blueprint("api", __name__, url_prefix="/api")

SELECT_SQL = (
    "SELECT n.id, n.title, n.body, n.created, u.username AS author "
    "FROM notes n JOIN users u ON n.author_id = u.id "
)


def to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "body": row["body"],
        "author": row["author"],
        "created": row["created"],
    }


@bp.get("/notes")
def list_notes():
    rows = get_db().execute(SELECT_SQL + "ORDER BY n.id DESC").fetchall()
    return jsonify(count=len(rows), notes=[to_dict(r) for r in rows])


@bp.get("/notes/<int:note_id>")
def get_note(note_id):
    row = get_db().execute(
        SELECT_SQL + "WHERE n.id = ?", (note_id,)
    ).fetchone()
    if row is None:
        abort(404, "笔记不存在。")
    return jsonify(note=to_dict(row))


@bp.post("/notes")
def create_note():
    if g.user is None:
        return jsonify(error="请先登录网页端，再调用该接口。"), 401

    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    body = str(data.get("body", "")).strip()

    if not title or not body:
        return jsonify(error="title 和 body 都是必填项。"), 400
    if len(title) > 100:
        return jsonify(error="title 最多 100 个字符。"), 400

    db = get_db()
    cursor = db.execute(
        "INSERT INTO notes (title, body, author_id) VALUES (?, ?, ?)",
        (title, body, g.user["id"]),
    )
    db.commit()
    row = db.execute(
        SELECT_SQL + "WHERE n.id = ?", (cursor.lastrowid,)
    ).fetchone()
    return jsonify(note=to_dict(row)), 201


@bp.delete("/notes/<int:note_id>")
def delete_note(note_id):
    if g.user is None:
        return jsonify(error="请先登录网页端，再调用该接口。"), 401

    row = get_db().execute(
        "SELECT author_id FROM notes WHERE id = ?", (note_id,)
    ).fetchone()
    if row is None:
        abort(404, "笔记不存在。")
    if row["author_id"] != g.user["id"]:
        return jsonify(error="只能删除自己的笔记。"), 403

    db = get_db()
    db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()
    return "", 204
