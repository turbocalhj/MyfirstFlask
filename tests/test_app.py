"""用 Flask 自带的测试客户端跑接口，不需要启动服务器。

运行：python -m unittest discover -s tests -v
"""
import os
import tempfile
import unittest

from app import create_app
from app.db import init_db


class NotesAppTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)

        # 学习点：应用工厂让测试可以使用独立的临时数据库
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "DATABASE": self.db_path,
            }
        )
        with self.app.app_context():
            init_db()

        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.db_path)

    def register_and_login(self, username="alice", password="secret123"):
        self.client.post(
            "/auth/register", data={"username": username, "password": password}
        )
        self.client.post(
            "/auth/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("还没有笔记", response.get_data(as_text=True))

    def test_register_login_and_create_note(self):
        self.register_and_login()

        response = self.client.post(
            "/create",
            data={"title": "我的第一篇笔记", "body": "Flask 真好用"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("我的第一篇笔记", html)
        self.assertIn("Flask 真好用", html)

    def test_create_requires_login(self):
        response = self.client.get("/create", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("请先登录", response.get_data(as_text=True))

    def test_search(self):
        self.register_and_login()
        self.client.post("/create", data={"title": "SQL 注入", "body": "参数化查询"})
        html = self.client.get("/?q=注入").get_data(as_text=True)
        self.assertIn("SQL 注入", html)

    def test_json_api(self):
        self.register_and_login()

        response = self.client.post(
            "/api/notes", json={"title": "API 笔记", "body": "来自 JSON 接口"}
        )
        self.assertEqual(response.status_code, 201)
        note_id = response.get_json()["note"]["id"]

        payload = self.client.get("/api/notes").get_json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["notes"][0]["title"], "API 笔记")

        # 未登录不能写接口
        self.client.post("/auth/logout")
        self.assertEqual(
            self.client.post("/api/notes", json={"title": "x", "body": "y"}).status_code,
            401,
        )

        # 404 在 /api 下返回 JSON
        self.assertEqual(
            self.client.get(f"/api/notes/{note_id + 999}").status_code, 404
        )


if __name__ == "__main__":
    unittest.main()
