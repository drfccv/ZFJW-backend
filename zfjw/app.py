"""Flask 应用工厂。"""
import urllib3
from flask import Flask
from flask_cors import CORS


def create_app():
    """创建并装配 Flask 应用。"""
    # 教务系统站点普遍使用自签/不匹配的证书，禁用 SSL 告警
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    app = Flask(__name__)
    CORS(app)

    from zfjw.routes import register_routes
    register_routes(app)

    # 自动生成的接口文档（/api/docs、/api/openapi.json），由 API_DOCS 开关控制
    from zfjw.docs import register_docs
    register_docs(app)

    # 初始化成绩推送定时任务（模块级标志防止多 worker 重复启动）
    from zfjw.tasks import init_scheduler
    init_scheduler(app)

    return app
