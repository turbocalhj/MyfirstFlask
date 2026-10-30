"""应用工厂（Application Factory）。

学习点 1：为什么用 create_app() 而不是模块级的 app = Flask(__name__)？
  - 测试时可以传入不同的配置（见 tests/test_app.py）
  - 同一个进程可以创建多个应用实例
  - 避免循环导入：蓝图在工厂内部才被导入并注册
"""
import os
from datetime import datetime
from importlib.metadata import version as pkg_version

from flask import Flask, jsonify, render_template, request


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    # 学习点 2：配置可以有默认值，也能被环境变量覆盖（配合 python-dotenv 读取 .env）。
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key-change-me"),
        # SQLite 数据库放在 instance 目录，不会污染源码目录，也不会被提交到 git
        DATABASE=os.environ.get(
            "DATABASE", os.path.join(app.instance_path, "notes.sqlite")
        ),
    )

    if test_config is not None:
        # 测试时整体覆盖配置，例如把 DATABASE 指向临时文件
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    # 数据库：注册 teardown 回调与 `flask init-db` 命令
    from . import db

    db.init_app(app)

    # 学习点 3：蓝图（Blueprint）把一组相关的路由拆到独立模块，便于维护
    from . import api, auth, notes

    app.register_blueprint(auth.bp)
    app.register_blueprint(notes.bp)
    app.register_blueprint(api.bp)

    # 学习点 4：Jinja2 自定义过滤器，模板里写 {{ note['created']|datetimeformat }}
    @app.template_filter("datetimeformat")
    def datetimeformat(value, fmt="%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime(fmt)
        except (TypeError, ValueError):
            return value

    # 学习点 5：上下文处理器，让所有模板都能直接用到这些变量
    @app.context_processor
    def inject_globals():
        return {
            "app_name": "Flask 学习笔记",
            "flask_version": pkg_version("flask"),
        }

    # 学习点 6：统一错误处理，同一套代码同时服务 HTML 页面和 JSON 接口
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify(error="Not Found", message=error.description), 404
        return render_template("errors/404.html", error=error), 404

    @app.errorhandler(500)
    def server_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error="Internal Server Error"), 500
        return render_template("errors/500.html"), 500

    return app
