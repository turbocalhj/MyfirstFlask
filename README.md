# Flask 学习笔记

一个用 Flask 写的轻量笔记站：支持注册登录、笔记增删改查、关键词搜索，同一份代码同时提供 HTML 页面和 JSON API。
项目刻意保持小体量，但把 Flask 常用的核心能力都串了一遍，适合作为初学者的第一个完整项目。

## 功能

- 注册 / 登录 / 退出（密码哈希存储，Session 保存登录状态）
- 笔记列表、关键词搜索、详情页
- 笔记新增、编辑、删除（只有作者本人可以修改和删除）
- JSON API：`GET /api/notes`、`GET /api/notes/<id>`、`POST /api/notes`、`DELETE /api/notes/<id>`
- 统一错误处理：页面请求返回 404/500 模板，`/api/*` 请求返回 JSON
- 自定义模板过滤器与上下文处理器
- 单元测试（Flask `test_client`，无需启动服务器）

## 技术栈

| 组件 | 用途 |
| --- | --- |
| Flask 3.1 | Web 框架：路由、Blueprint、Session、CLI |
| Jinja2 | 模板继承与页面渲染 |
| SQLite + sqlite3 | 数据存储，零外部依赖 |
| Werkzeug | 密码哈希、WSGI、开发服务器 |
| python-dotenv | 读取 `.env` 配置 |
| unittest | 单元测试 |

## 快速开始

```powershell
# 1. 创建并激活虚拟环境（项目里已有 .venv 可跳过创建）
python -m venv .venv
.venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 准备配置文件（可选，不建也有开发默认值）
copy .env.example .env

# 4. 初始化数据库（会建表，重复执行会清空数据）
flask --app run init-db

# 5. 启动开发服务器
python run.py
```

打开 <http://127.0.0.1:5000>。开发模式下修改代码会自动重载，出错会显示交互式调试页。

演示账号：`demo / demo123456`（执行 `flask --app run init-db` 后该账号会被清空，需要重新注册）。

## 目录结构

```text
.
├─ run.py                  # 入口：create_app() 并启动开发服务器
├─ requirements.txt
├─ .env.example            # 配置模板，复制为 .env 使用
├─ app/
│  ├─ __init__.py          # 应用工厂、过滤器、上下文处理器、错误处理
│  ├─ db.py                # SQLite 连接（g）、teardown、flask init-db 命令
│  ├─ schema.sql           # users / notes 表结构
│  ├─ auth.py              # 认证蓝图：注册、登录、登出、login_required
│  ├─ notes.py             # 笔记蓝图：列表、搜索、详情、增删改
│  ├─ api.py               # JSON API 蓝图
│  ├─ templates/           # base.html + 页面模板 + 错误页
│  └─ static/style.css
├─ tests/
│  └─ test_app.py          # 5 个单元测试
└─ instance/               # 运行时生成，存 SQLite 文件，已加入 .gitignore
```

## 学习地图

代码中带有 `学习点 1` ~ `学习点 13` 的注释，按下面的顺序阅读效果最好：

| 顺序 | 文件 | 关键知识点 |
| --- | --- | --- |
| 1 | `app/__init__.py` | 应用工厂、配置覆盖、蓝图注册、模板过滤器、上下文处理器、统一错误处理 |
| 2 | `app/db.py` | `g` 的请求级生命周期、`teardown_appcontext`、自定义 CLI 命令 |
| 3 | `app/auth.py` | Session 与签名 Cookie、`before_app_request`、装饰器 `login_required`、密码哈希 |
| 4 | `app/notes.py` | URL 转换器 `<int:note_id>`、参数化查询防 SQL 注入、作者权限校验 |
| 5 | `app/api.py` | `jsonify`、`request.get_json()`、HTTP 状态码语义（201/401/403/404/204） |
| 6 | `app/templates/base.html` | 模板继承、`block`、`get_flashed_messages`、`url_for` |
| 7 | `tests/test_app.py` | `test_client`、临时数据库、测试隔离 |

## JSON API

所有接口都在 `/api` 前缀下，返回 `application/json`。

### 查看列表

```powershell
curl http://127.0.0.1:5000/api/notes
```

```json
{
  "count": 2,
  "notes": [
    {
      "id": 2,
      "title": "蓝图把路由按职责拆开",
      "body": "auth 负责 /auth/*，notes 负责页面，api 负责 /api/*。",
      "author": "demo",
      "created": "2026-10-30 14:12:27"
    }
  ]
}
```

### 新建笔记（需要先登录，接口复用网页的 Session）

```powershell
# 登录并把会话 cookie 存到 cookies.txt（登录接口是网页表单，返回 302）
curl -c cookies.txt -X POST http://127.0.0.1:5000/auth/login -d "username=demo&password=demo123456"

# 带 cookie 调用写接口
curl -b cookies.txt -H "Content-Type: application/json" ^
  -d "{\"title\":\"API 测试\",\"body\":\"通过 JSON 创建\"}" ^
  http://127.0.0.1:5000/api/notes
```

成功返回 `201`：

```json
{"note": {"id": 3, "title": "API 测试", "body": "通过 JSON 创建", "author": "demo", "created": "..."}}
```

错误约定：

| 场景 | 状态码 | 返回 |
| --- | --- | --- |
| 未登录 | 401 | `{"error": "请先登录网页端，再调用该接口。"}` |
| 缺少 title/body | 400 | `{"error": "title 和 body 都是必填项。"}` |
| 删除别人的笔记 | 403 | `{"error": "只能删除自己的笔记。"}` |
| 笔记不存在 | 404 | `{"error": "Not Found", "message": "笔记不存在。"}` |

## 运行测试

```powershell
python -m unittest discover -s tests -t . -v
```

## 常见问题

**启动时报 `flask init-db` 找不到？**
先确认当前目录是项目根目录，并激活了虚拟环境。也可以直接用 Python 模块方式：`python -m flask --app run init-db`。

**改了数据库表结构怎么生效？**
SQLite 的建表脚本在 `app/schema.sql`，执行 `flask --app run init-db` 会重建表（数据会清空）。想保留数据的话，请手动写迁移脚本。

**为什么数据库在 `instance/` 里？**
Flask 的 `instance` 目录用于存放「不该进版本库」的运行时数据，`SECRET_KEY` 配置和 SQLite 文件都适合放这里，已加入 `.gitignore`。

**生产环境能直接用 `python run.py` 吗？**
不能。`app.run()` 是开发服务器，只适合本地调试。生产环境应使用 Gunicorn / Waitress 等 WSGI 服务器，并设置真实的 `SECRET_KEY`。

**页面上的时间为什么和系统时间一致？**
表结构的默认值使用了 `datetime('now', 'localtime')`，直接按本地时间入库，省去初学者处理时区的麻烦。多时区场景应统一存 UTC 再在展示层转换。

## 可以继续练的方向

1. 给笔记加标签：新增 `tags` 表，用多对多关系练习 JOIN。
2. 把裸 SQL 换成 SQLAlchemy 或 Flask-SQLAlchemy，对比 ORM 与手写 SQL 的差异。
3. 加分页（`?page=2`）与按时间/作者筛选。
4. 给 API 加 Token 鉴权，区分网页 Session 与程序调用。
5. 用 `pytest` + fixture 重写测试，体验更简洁的测试组织方式。
