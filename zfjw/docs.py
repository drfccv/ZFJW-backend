"""自动生成 OpenAPI 3.0 文档，并提供 Swagger UI 页面。

设计目标：**文档从代码推导，永不与实现脱节**。

推导来源：
- 路由与 HTTP 方法 —— 反射 Flask `url_map`
- 请求参数        —— AST 解析视图函数源码中的
                     `data.get('x')` / `data.get('x', 默认值)` / `request.args.get('x')`，
                     并识别 `if not all([...]): return jsonify({"code": 400, ...})`
                     这类必填校验，自动标记 required
- 接口说明        —— 函数 docstring（`@handle_errors` 已用 functools.wraps 保留）
- 参数类型        —— 优先取 `PARAM_META`，否则由默认值推断

对外提供：
- `GET /api/openapi.json`   OpenAPI 3.0 规范
- `GET /api/docs`           Swagger UI 页面（可直接 "Try it out" 调试）

开关：环境变量 `API_DOCS`（`1/true/yes/on` 开启，`0/false/no/off` 关闭）。
未设置时：`FLASK_ENV=production` 默认关闭，其余环境默认开启。
"""
import ast
import inspect
import os
import re
import textwrap
from typing import Any, Dict, List, Optional, Set

from flask import Blueprint, jsonify

# ── 可选配置 ────────────────────────────────────────────────────────────

#: Swagger UI 静态资源地址；可通过 API_DOCS_ASSETS 指向本地目录（离线部署）
SWAGGER_UI_CDN = "https://unpkg.com/swagger-ui-dist@5.17.14"

#: 蓝图名 -> 文档分组标题
TAG_TITLES = {
    "auth": "认证",
    "academic": "学业（信息 / 成绩 / 考试 / 课表）",
    "course": "选课",
    "evaluate": "教学评价",
    "classroom": "教室",
    "school": "学校配置",
    "push": "成绩推送",
    "system": "系统",
}

#: 返回体 code 含义，写入文档总览
STATUS_CODES = {
    "1000": "成功",
    "400": "请求参数不完整或为空",
    "1001": "获取验证码成功（需继续调用 /api/login_with_kaptcha）",
    "1002": "用户名或密码不正确",
    "1004": "验证码输入错误",
    "1005": "获取内容为空",
    "1006": "未登录或登录已过期，请重新登录",
    "1014": "无当前学年学期数据",
    "2333": "教务系统服务异常或学校配置不完整",
    "998": "教务系统返回了业务错误提示",
    "999": "服务器内部错误",
}

#: 参数元信息：补全类型 / 说明 / 示例。未列出的参数由默认值推断类型。
PARAM_META: Dict[str, Dict[str, Any]] = {
    "cookies": {
        "type": "object",
        "description": "登录接口返回的 cookies 字典（须含 route 等负载均衡路由 cookie）",
        "example": {"JSESSIONID": "XXXXXXXX", "route": "XXXXXXXXXXXXXXXX"},
    },
    "school_name": {
        "type": "string",
        "description": "学校名称，与 base_url 二选一（推荐）",
        "example": "九江学院",
    },
    "base_url": {
        "type": "string",
        "description": "教务系统地址，与 school_name 二选一",
        "example": "https://zhjw1.jju.edu.cn",
    },
    "sid": {"type": "string", "description": "学号", "example": "20240202932"},
    "password": {"type": "string", "description": "密码（明文，服务端 RSA 加密后提交）", "format": "password"},
    "year": {"type": "integer", "description": "学年，如 2025", "example": 2025},
    "term": {"type": "integer", "description": "学期：1=第一学期，2=第二学期，0=整个学年", "example": 1},
    "openid": {"type": "string", "description": "微信小程序 openid"},
    "code": {"type": "string", "description": "微信登录 code（wx.login 获取）"},
    "course_id": {"type": "string", "description": "课程号"},
    "do_id": {"type": "string", "description": "选课批次 / 教学班标识"},
    "jxb_id": {"type": "string", "description": "教学班 ID"},
    "kch_id": {"type": "string", "description": "课程 ID"},
    "kklxdm": {"type": "string", "description": "课程类别代码", "example": "1"},
    "evaluation_data": {
        "type": "object",
        "description": '评价项分数，形如 {"items": [{"input_name": "pjzbxm_xxx", "score": "100"}]}',
        "example": {"items": [{"input_name": "pjzbxm_0001", "score": "100"}]},
    },
    "comment": {"type": "string", "description": "评语文本"},
    "block": {"type": "integer", "description": "板块序号（block_id 的别名）"},
    "block_id": {"type": "integer", "description": "板块序号"},
    "campus_id": {"type": "string", "description": "校区 ID，可通过 /api/campus_list 获取", "example": "1"},
    "building": {"type": "string", "description": "教学楼名称，不传表示全部"},
    "weeks": {"description": "周次，支持单个数字、数组或逗号分隔字符串", "example": 3},
    "day_of_weeks": {"description": "星期，1=周一…7=周日，支持单个/数组/逗号分隔", "example": "1,3"},
    "time_slots": {"description": "节次，支持单个数字、数组或范围字符串", "example": "2-3"},
    "subscribe_status": {"type": "string", "description": "订阅状态", "example": "accept"},
    "comment_name": {"type": "string", "description": "评语字段名（兼容用，默认 py）"},
    "csrf_token": {"type": "string", "description": "登录页解析出的 CSRF token（来自 /api/login 响应）"},
    "modulus": {"type": "string", "description": "RSA 公钥 modulus（来自 /api/login 响应）"},
    "exponent": {"type": "string", "description": "RSA 公钥 exponent（来自 /api/login 响应）"},
    "kaptcha": {"type": "string", "description": "用户识别的图形验证码"},
    "kaptcha_pic": {"type": "string", "description": "验证码图片（base64，仅响应中返回）"},
}

#: 通用鉴权参数：所有需要已登录会话的接口共享
COMMON_AUTH_KEYS = ("cookies", "school_name", "base_url")

#: 补充参数：部分接口把请求数据整体透传（如 **kwargs），AST 无法静态提取，
#: 在此手动声明。键为 Flask endpoint。
EXTRA_PARAMS: Dict[str, Dict[str, Dict[str, Any]]] = {
    # 本接口把除 base_url 外的全部请求字段透传给 Client.login_with_kaptcha
    "auth.login_with_kaptcha": {
        "sid": {"required": True},
        "csrf_token": {"required": True},
        "cookies": {"required": True},
        "password": {"required": True},
        "modulus": {"required": True},
        "exponent": {"required": True},
        "kaptcha": {"required": True},
    },
}


# ── 工具函数 ────────────────────────────────────────────────────────────

def docs_enabled() -> bool:
    """文档是否开启：显式 API_DOCS 优先，否则非 production 默认开启。"""
    raw = os.environ.get("API_DOCS")
    if raw is not None:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return os.environ.get("FLASK_ENV") != "production"


def _literal(node: ast.AST) -> Any:
    """把 AST 字面量节点还原成 Python 值；无法还原时返回 None。"""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_literal(e) for e in node.elts]
    if isinstance(node, ast.Dict):
        return {_literal(k): _literal(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = _literal(node.operand)
        return -inner if isinstance(inner, (int, float)) else None
    return None


def _is_400_guard(node: ast.If) -> bool:
    """判断是否为 `if <缺少必填项>: return jsonify({"code": 400, ...})` 形式的校验。"""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) \
                and sub.func.id == "jsonify" and sub.args:
            arg = sub.args[0]
            if isinstance(arg, ast.Dict):
                for key, val in zip(arg.keys, arg.values):
                    if getattr(key, "value", None) == "code" and getattr(val, "value", None) == 400:
                        return True
    return False


def _names_in(node: ast.AST) -> Set[str]:
    """收集表达式里出现的变量名。"""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _need_true(node: ast.AST) -> Set[str]:
    """求「表达式为真时必然非空的变量」集合。"""
    # a and b  -> 两者都要为真
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        out: Set[str] = set()
        for value in node.values:
            out |= _need_true(value)
        return out
    # a or b -> 只需一个为真，无法断定具体哪个
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        return set()
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _need_false(node.operand)
    if isinstance(node, ast.Name):
        return {node.id}
    # all([a, b, ...]) -> 全部为真
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id == "all" and node.args:
        arg = node.args[0]
        elts = arg.elts if isinstance(arg, (ast.List, ast.Tuple)) else []
        out = set()
        for elt in elts:
            out |= _names_in(elt)
        return out
    return set()


def _need_false(node: ast.AST) -> Set[str]:
    """求「表达式为假时必然非空的变量」集合。

    这让 `if not sid or not password:` 正确解析为 sid/password 必填，
    `if (not base_url and not school_name):` 则因「至少一个」而不产出必填项。
    """
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _need_true(node.operand)
    # 全部为假 -> 各分支都要为假
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        out: Set[str] = set()
        for value in node.values:
            out |= _need_false(value)
        return out
    # 只需一个为假，无法断定具体哪个
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        return set()
    return set()


def _module_functions(view) -> Dict[str, ast.FunctionDef]:
    """解析视图函数所在模块，返回其中的模块级函数定义。"""
    module = inspect.getmodule(inspect.unwrap(view))
    if module is None:
        return {}
    try:
        source = textwrap.dedent(inspect.getsource(module))
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError):
        return {}
    return {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}


def _scan_params(fn_node: ast.FunctionDef,
                 module_funcs: Dict[str, ast.FunctionDef],
                 depth: int = 0,
                 seen: Optional[Set[str]] = None) -> Dict[str, Any]:
    """从函数体提取请求参数。

    - 递归跟进同模块 helper（如 `_fetch_schedule_direct(data, ...)`），
      因为部分路由把参数读取放在被调用的辅助函数里
    """
    seen = seen or set()
    params: Dict[str, Any] = {}
    required: Set[str] = set()

    for node in ast.walk(fn_node):
        # data.get('x'[, default]) / request.args.get('x')
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "get":
            recv = node.func.value
            recv_name = recv.id if isinstance(recv, ast.Name) else (
                f"{getattr(recv, 'value', None).id}.{recv.attr}"
                if isinstance(recv, ast.Attribute) and isinstance(getattr(recv, "value", None), ast.Name)
                else None
            )
            if recv_name in ("data", "payload", "request.args", "request.json") \
                    and node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                name = node.args[0].value
                default = _literal(node.args[1]) if len(node.args) > 1 else None
                has_default = len(node.args) > 1
                if name not in params:
                    params[name] = {"default": default, "has_default": has_default}

        # if not (...): return 400  ->  必填项
        if isinstance(node, ast.If) and _is_400_guard(node):
            required |= _need_false(node.test)

        # 递归解析同模块 helper：调用时传了 data
        if depth < 2 and isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            helper = module_funcs.get(node.func.id)
            if helper is not None and node.func.id not in seen \
                    and any(isinstance(a, ast.Name) and a.id in ("data", "payload") for a in node.args):
                seen.add(node.func.id)
                sub = _scan_params(helper, module_funcs, depth + 1, seen)
                for k, v in sub["params"].items():
                    params.setdefault(k, v)
                required |= sub["required"]

    return {"params": params, "required": required}


def _schema_for(name: str, info: Dict[str, Any]) -> Dict[str, Any]:
    """把参数信息转成 OpenAPI schema。"""
    meta = PARAM_META.get(name, {})
    schema: Dict[str, Any] = {}
    if "type" in meta:
        schema["type"] = meta["type"]
    elif info.get("has_default"):
        default = info.get("default")
        if isinstance(default, bool):
            schema["type"] = "boolean"
        elif isinstance(default, int):
            schema["type"] = "integer"
        elif isinstance(default, float):
            schema["type"] = "number"
        elif isinstance(default, list):
            schema["type"] = "array"
        elif isinstance(default, dict):
            schema["type"] = "object"
        else:
            schema["type"] = "string"
    else:
        schema["type"] = "string"

    if "format" in meta:
        schema["format"] = meta["format"]
    if info.get("has_default") and info.get("default") is not None:
        schema["default"] = info["default"]
    if "example" in meta:
        schema["example"] = meta["example"]
    schema["description"] = meta.get("description", "")
    if not schema["description"]:
        schema.pop("description")
    return schema


def _openapi_path(rule: str) -> str:
    """Flask 的 `<name>` / `<converter:name>` 转成 OpenAPI 的 `{name}`。"""
    return re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", rule)


def _summary(view) -> str:
    """接口摘要：docstring 首行；没有则用函数名。"""
    doc = (inspect.getdoc(inspect.unwrap(view)) or "").strip()
    if doc:
        return doc.splitlines()[0]
    return inspect.unwrap(view).__name__


def _description(view) -> str:
    """接口详细说明：docstring 去掉首行后的剩余内容。"""
    doc = (inspect.getdoc(inspect.unwrap(view)) or "").strip()
    lines = doc.splitlines()
    return "\n".join(lines[1:]).strip() if len(lines) > 1 else ""


# ── 规范构建 ────────────────────────────────────────────────────────────

def build_openapi_spec(app, spec_url: str = "/api/openapi.json") -> Dict[str, Any]:
    """根据 Flask 应用自动生成 OpenAPI 3.0 规范。"""
    paths: Dict[str, Any] = {}

    for rule in sorted(app.url_map.iter_rules(), key=lambda r: (r.rule, sorted(r.methods))):
        if rule.endpoint == "static" or rule.endpoint.startswith("docs."):
            continue

        view = app.view_functions[rule.endpoint]
        module_funcs = _module_functions(view)
        try:
            fn_node = ast.parse(textwrap.dedent(inspect.getsource(inspect.unwrap(view)))).body[0]
        except (OSError, TypeError, SyntaxError, IndexError):
            fn_node = None

        scanned = _scan_params(fn_node, module_funcs) if fn_node else {"params": {}, "required": set()}
        found: Dict[str, Any] = dict(scanned["params"])
        required: Set[str] = set(scanned["required"])

        # 合并手动声明的补充参数（用于 **kwargs 透传等静态分析不到的情况）
        for name, extra in EXTRA_PARAMS.get(rule.endpoint, {}).items():
            found.setdefault(name, {"default": None, "has_default": False})
            if extra.get("required"):
                required.add(name)

        # 只保留真实存在的请求参数，过滤掉校验表达式里的局部变量
        required &= set(found)

        tag = rule.endpoint.split(".")[0]

        # path 参数（如 /api/school/<school_name>）
        path_param_names = set(rule.arguments)

        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            operation: Dict[str, Any] = {
                "tags": [TAG_TITLES.get(tag, tag)],
                "summary": _summary(view),
                "operationId": f"{rule.endpoint}_{method.lower()}",
                "responses": {
                    "200": {
                        "description": "统一响应格式",
                        "content": {"application/json": {
                            "schema": {"$ref": "#/components/schemas/ApiResponse"}}},
                    }
                },
            }
            desc = _description(view)
            if desc:
                operation["description"] = desc

            # ① path 参数
            parameters: List[Dict[str, Any]] = []
            for name in sorted(path_param_names):
                parameters.append({
                    "name": name, "in": "path", "required": True,
                    "schema": {"type": "string"},
                    "description": "学校名称" if name == "school_name" else "",
                })
                for p in parameters:
                    if not p.get("description"):
                        p.pop("description", None)

            # ② 请求体 / 查询参数
            body_params = {k: v for k, v in found.items() if k not in path_param_names}
            common = {k: v for k, v in body_params.items() if k in COMMON_AUTH_KEYS}
            specific = {k: v for k, v in body_params.items() if k not in COMMON_AUTH_KEYS}

            if method == "GET":
                for name, info in sorted(body_params.items()):
                    parameters.append({
                        "name": name, "in": "query",
                        "required": name in required,
                        "schema": _schema_for(name, info),
                    })
            elif body_params:
                properties: Dict[str, Any] = {}
                required_list: List[str] = []
                for name, info in sorted(specific.items()):
                    properties[name] = _schema_for(name, info)
                # required 可能包含公共参数（如 cookies），需一并声明
                for name in sorted(required):
                    if name in body_params:
                        required_list.append(name)

                schema: Dict[str, Any] = {"type": "object"}
                if properties:
                    schema["properties"] = properties
                if required_list:
                    schema["required"] = required_list

                merged: Dict[str, Any] = schema
                if common:
                    # 与通用鉴权参数合并
                    merged = {"allOf": [{"$ref": "#/components/schemas/AuthParams"}, schema]}
                operation["requestBody"] = {
                    "required": True,
                    "content": {"application/json": {"schema": merged}},
                }

            if parameters:
                operation["parameters"] = parameters

            paths.setdefault(_openapi_path(rule.rule), {})[method.lower()] = operation

    from zfjw import __version__

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "ZFJW Backend API",
            "version": __version__,
            "description": (
                "正方教务系统后端 API。\n\n"
                "**认证方式**：登录接口返回 `cookies`，后续接口在请求体中携带即可。\n\n"
                "**通用参数**：需要已登录会话的接口都接受 `cookies` 以及 "
                "`school_name` / `base_url`（二者至少提供一个）。\n\n"
                "**返回码含义**：\n"
                + "\n".join(f"- `{code}` — {text}" for code, text in STATUS_CODES.items())
            ),
        },
        "servers": [{"url": "/", "description": "当前服务"}],
        "tags": [{"name": title} for title in TAG_TITLES.values()],
        "paths": paths,
        "components": {
            "schemas": {
                "AuthParams": {
                    "type": "object",
                    "properties": {
                        name: _schema_for(name, {"has_default": False})
                        for name in COMMON_AUTH_KEYS
                    },
                    "description": "通用鉴权参数；cookies 为登录接口返回，school_name / base_url 至少提供一个",
                },
                "ApiResponse": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "integer", "description": "业务状态码",
                                 "example": 1000},
                        "msg": {"type": "string", "description": "提示信息",
                                "example": "操作成功"},
                        "data": {"type": "object", "description": "业务数据，随接口而异"},
                    },
                    "required": ["code", "msg"],
                },
            }
        },
        "x-spec-url": spec_url,
    }


# ── Swagger UI 页面 ─────────────────────────────────────────────────────

_SWAGGER_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>ZFJW Backend API 文档</title>
  <link rel="stylesheet" href="{assets}/swagger-ui.css">
  <style>
    body {{ margin: 0; }}
    .topbar {{ display: none; }}
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="{assets}/swagger-ui-bundle.js"></script>
  <script>
    window.onload = function () {{
      window.ui = SwaggerUIBundle({{
        url: "{spec_url}",
        dom_id: "#swagger-ui",
        docExpansion: "list",
        defaultModelsExpandDepth: -1,
        displayRequestDuration: true,
        persistAuthorization: true,
        tryItOutEnabled: true,
        filter: true,
        tagsSorter: "alpha"
      }});
    }};
  </script>
</body>
</html>
"""


def render_swagger_ui(spec_url: str = "/api/openapi.json") -> str:
    """渲染 Swagger UI 页面（可指向相对路径，便于导出静态文件）。"""
    assets = os.environ.get("API_DOCS_ASSETS", SWAGGER_UI_CDN).rstrip("/")
    return _SWAGGER_HTML.format(assets=assets, spec_url=spec_url)


# ── 蓝图 ────────────────────────────────────────────────────────────────

bp = Blueprint("docs", __name__)


@bp.route("/openapi.json", methods=["GET"])
def openapi_spec():
    """OpenAPI 3.0 规范（由代码自动生成）。"""
    if not docs_enabled():
        return jsonify({"code": 404, "msg": "Not Found"}), 404
    from flask import current_app
    return jsonify(build_openapi_spec(current_app))


@bp.route("/docs", methods=["GET"])
def swagger_ui():
    """Swagger UI 交互式接口文档。"""
    if not docs_enabled():
        return jsonify({"code": 404, "msg": "Not Found"}), 404
    from flask import Response
    return Response(render_swagger_ui(), mimetype="text/html")


def register_docs(app) -> None:
    """把文档蓝图挂载到应用（统一 /api 前缀）。"""
    app.register_blueprint(bp, url_prefix="/api")
