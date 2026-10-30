"""SQLite 数据层。

学习点 7：Flask 的 `g` 对象是「一次请求内的临时存放点」。
  - 每个请求第一次用到数据库时建立连接，缓存在 g 上
  - 请求结束时 teardown_appcontext 自动关闭连接，不必手动管理
"""
import sqlite3

import click
from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        # row_factory 让查询结果支持 row["title"] 这种按列名取值的方式
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))


@click.command("init-db")
def init_db_command():
    """重建数据库表（会清空已有数据）。"""
    init_db()
    click.echo("数据库已初始化：instance/notes.sqlite")


def init_app(app):
    app.teardown_appcontext(close_db)
    # 学习点 8：把自定义命令挂到 flask CLI 上，之后可以执行 `flask init-db`
    app.cli.add_command(init_db_command)
