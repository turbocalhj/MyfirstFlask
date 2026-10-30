"""入口文件：python run.py 启动开发服务器（会自动重载）。

也可以使用 Flask CLI：
    flask --app run run --debug
    flask --app run init-db      # 首次运行前先建表
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
