"""笔记蓝图：HTML 页面（列表 / 搜索 / 详情 / 新增 / 编辑 / 删除）。

学习点 12：路由可以带类型转换器，例如 <int:note_id>，非整数会直接返回 404。
"""
from flask import (
    Blueprint,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from .auth import login_required
from .db import get_db

bp = Blueprint("notes", __name__)

LIST_SQL = (
    "SELECT n.id, n.title, n.body, n.created, n.author_id, u.username "
    "FROM notes n JOIN users u ON n.author_id = u.id "
)


@bp.route("/")
def index():
    keyword = request.args.get("q", "").strip()
    db = get_db()

    if keyword:
        # 参数化查询：绝对不要把用户输入直接拼进 SQL，避免 SQL 注入
        notes = db.execute(
            LIST_SQL + "WHERE n.title LIKE ? OR n.body LIKE ? ORDER BY n.id DESC",
            (f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
    else:
        notes = db.execute(LIST_SQL + "ORDER BY n.id DESC").fetchall()

    return render_template("index.html", notes=notes, q=keyword)


def get_note(note_id):
    note = get_db().execute(
        LIST_SQL + "WHERE n.id = ?", (note_id,)
    ).fetchone()
    if note is None:
        abort(404, f"笔记 id={note_id} 不存在。")
    return note


@bp.route("/note/<int:note_id>")
def detail(note_id):
    return render_template("notes/detail.html", note=get_note(note_id))


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        error = None

        if not title:
            error = "标题不能为空。"
        elif len(title) > 100:
            error = "标题最多 100 个字符。"
        elif not body:
            error = "正文不能为空。"

        if error is None:
            db = get_db()
            cursor = db.execute(
                "INSERT INTO notes (title, body, author_id) VALUES (?, ?, ?)",
                (title, body, g.user["id"]),
            )
            db.commit()
            flash("笔记已保存。", "success")
            return redirect(url_for("notes.detail", note_id=cursor.lastrowid))

        flash(error, "error")

    return render_template("notes/form.html", note=None)


@bp.route("/note/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit(note_id):
    note = get_note(note_id)

    # 权限演示：只有作者本人可以修改
    if note["author_id"] != g.user["id"]:
        flash("只能编辑自己写的笔记。", "error")
        return redirect(url_for("notes.detail", note_id=note_id))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        error = None

        if not title:
            error = "标题不能为空。"
        elif len(title) > 100:
            error = "标题最多 100 个字符。"
        elif not body:
            error = "正文不能为空。"

        if error is None:
            db = get_db()
            db.execute(
                "UPDATE notes SET title = ?, body = ? WHERE id = ?",
                (title, body, note_id),
            )
            db.commit()
            flash("笔记已更新。", "success")
            return redirect(url_for("notes.detail", note_id=note_id))

        flash(error, "error")
        note = {"id": note_id, "title": title, "body": body}

    return render_template("notes/form.html", note=note)


@bp.post("/note/<int:note_id>/delete")
@login_required
def delete(note_id):
    note = get_note(note_id)
    if note["author_id"] != g.user["id"]:
        flash("只能删除自己写的笔记。", "error")
        return redirect(url_for("notes.detail", note_id=note_id))

    get_db().execute("DELETE FROM notes WHERE id = ?", (note_id,))
    get_db().commit()
    flash("笔记已删除。", "success")
    return redirect(url_for("notes.index"))
