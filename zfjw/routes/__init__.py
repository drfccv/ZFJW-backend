"""路由蓝图注册。

各蓝图统一挂载在 `/api` 前缀下，路由路径已去除 `/api`，
以保证对外 URL 与旧版完全一致。
"""


def register_routes(app):
    """把所有蓝图注册到 Flask 应用。"""
    # 延迟导入，避免 zfjw.routes 包初始化与子模块相互导入造成循环
    from zfjw.routes import (
        academic,
        auth,
        classroom,
        course,
        evaluate,
        push,
        school,
        system,
    )

    blueprints = (
        auth.bp,
        academic.bp,
        course.bp,
        evaluate.bp,
        classroom.bp,
        school.bp,
        push.bp,
        system.bp,
    )
    for bp in blueprints:
        app.register_blueprint(bp, url_prefix="/api")
