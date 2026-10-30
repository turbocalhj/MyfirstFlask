"""认证蓝图：注册 / 登录 / 登出。

学习点 9：Flask 的 session 是「签名过的 cookie」——数据存在客户端，
但被 SECRET_KEY 签名，用户改不了内容。适合存 user_id 这类小数据。
"""
import functools

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.before_app_request
def load_logged_in_user():
    """学习点 10：请求开始前把当前用户放到 g.user，所有视图都能直接使用。"""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def login_required(view):
    """装饰器：未登录访问受保护页面时跳转到登录页。"""

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("请先登录。", "error")
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = None

        if not 3 <= len(username) <= 20:
            error = "用户名长度需要 3-20 个字符。"
        elif len(password) < 6:
            error = "密码至少 6 位。"
        else:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
            except db.IntegrityError:
                # 用户名唯一索引冲突：说明已被注册
                error = f"用户 {username} 已存在。"

        if error is None:
            flash("注册成功，请登录。", "success")
            return redirect(url_for("auth.login"))
        flash(error, "error")

    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user is None or not check_password_hash(
            user["password_hash"], password
        ):
            flash("用户名或密码不正确。", "error")
        else:
            # 学习点 11：登录成功只往 session 里写 user_id
            session.clear()
            session["user_id"] = user["id"]
            flash(f"欢迎回来，{user['username']}！", "success")
            return redirect(url_for("notes.index"))

    return render_template("auth/login.html")


@bp.post("/logout")
def logout():
    session.clear()
    flash("已退出登录。", "success")
    return redirect(url_for("notes.index"))
