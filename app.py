"""ZFJW Backend 服务入口。

生产环境通过 `app:app` 加载（见 Dockerfile），或用任意 WSGI 服务器指向本模块。
应用装配逻辑位于 `zfjw.app.create_app`，HTTP 路由见 `zfjw.routes`。
"""
import os

from zfjw.app import create_app

app = create_app()

if __name__ == '__main__':
    # 检查是否在生产环境
    is_production = os.environ.get('FLASK_ENV') == 'production'
    debug_mode = not is_production

    print("启动 ZFJW Backend API 服务...")
    print(f"运行模式: {'生产环境' if is_production else '开发环境'}")
    print("健康检查: http://localhost:5000/api/health")

    if is_production:
        print("提示: Flask 内置服务器不适合高并发，生产环境请用 Docker 部署或改用 gunicorn 等 WSGI 服务器")

    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
