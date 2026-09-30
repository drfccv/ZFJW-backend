# ZFJW-backend

![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

正方教务系统后端 API。用 Flask 封装为 RESTful 接口，支持 7 所高校的教务数据查询，
可作为微信小程序 / Web 应用的后端，避免前端直接处理登录加密与页面解析。

## 功能

- 登录（密码 / 验证码），返回 cookies 供后续接口复用
- 个人信息与学籍
- 成绩（总表 / 明细）
- 考试安排、课表
- 选课 / 退课、已选课程、板块课程、教学班查询
- 教学评价（列表 / 详情 / 保存 / 提交）
- 空教室查询（校区、教学楼、节次）
- 成绩变动推送（微信订阅消息，定时轮询）
- 多校支持，配置驱动（见 [学校配置](#学校配置)）


## 快速开始

需要 Python 3.12+（见 `.python-version`），依赖声明在 `pyproject.toml`、版本锁定在 `uv.lock`。

使用 [uv](https://docs.astral.sh/uv/)：

```bash
git clone https://github.com/drfccv/ZFJW-backend.git
cd ZFJW-backend
uv sync                 # 装好 Python 3.12 与全部依赖

# 可选：配置微信凭据以启用成绩推送
cp .env.example .env    # 填入 APPID / APPSECRET

uv run python app.py    # 服务运行在 http://localhost:5000
```

验证：`curl http://localhost:5000/api/health`

### Docker

```bash
cp .env.example .env    # 填入 APPID / APPSECRET
docker compose up -d
```

或使用 `docker run`：

```bash
docker build -t zfjw-backend .
docker run -p 5000:5000 --env-file .env zfjw-backend
```

> `APPID` / `APPSECRET` 只通过环境变量或 `.env` 注入，切勿提交到仓库。
> 未配置时仅「成绩推送」不可用，其余接口不受影响。

### 生产部署

```bash
docker compose up -d --build
```

如需更高并发，可改用 gunicorn：加进 `pyproject.toml` 的 `dependencies`（并 `uv lock`），
再把 Dockerfile 末尾的 `CMD` 换成：

```dockerfile
CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "app:app"]
```

## API 文档

文档由代码自动生成，随实现同步：

| 地址 | 说明 |
|---|---|
| `GET /api/docs` | Swagger UI，可直接 “Try it out” 调试 |
| `GET /api/openapi.json` | OpenAPI 3.0 规范 |

**开关**：环境变量 `API_DOCS`（`1/true/yes/on` 开启，`0/false/no/off` 关闭）；
未设置时 `FLASK_ENV=production` 默认关闭，其余环境默认开启。

**导出静态文件**：

```bash
python -m scripts.gen_api_docs               # 输出到 docs/
python -m scripts.gen_api_docs -o build/api  # 自定义输出目录
```

新增接口无需手动更新文档；参数类型/示例可在 `zfjw/docs.py` 的 `PARAM_META`、`EXTRA_PARAMS` 中补充。

### 接口一览

> Base URL 为 `http://localhost:5000/api`，数据格式 JSON。
> 认证基于 Session：请求体携带登录返回的 `cookies`，并配 `school_name` / `base_url`（二者至少一个）。
> 响应统一为 `{ "code": 1000, "msg": "...", "data": { ... } }`，`code` 含义见 `/api/docs` 总览。

| 分组 | 接口 |
|---|---|
| 认证 | `POST /api/login`、`/api/login_with_kaptcha`、`/api/get_captcha` |
| 学业 | `POST /api/info`、`/api/grade`、`/api/grade_detail`、`/api/exam`、`/api/schedule`、`/api/notifications` |
| 选课 | `POST /api/selected_courses`、`/api/block_courses`、`/api/course_classes`、`/api/select_course`、`/api/drop_course` |
| 教学评价 | `POST /api/evaluate_menu`、`/api/evaluate_detail`、`/api/evaluate_save`、`/api/evaluate_submit` |
| 教室 | `POST /api/campus_list`、`/api/building_list`、`/api/classroom` |
| 学校配置 | `GET /api/schools`、`/api/school/<school_name>`、`/api/school/<school_name>/captcha-required` |
| 成绩推送 | `POST /api/bind_openid`、`/api/subscribe_grade_push`、`/api/unsubscribe_grade_push`、`GET\|POST /api/grade_push_status` |
| 系统 | `GET /api/health` |

## 项目结构

```
ZFJW-backend/
├── app.py                     # 入口，暴露 app:app
├── config/
│   └── schools_config.json    # 学校配置
├── zfjw/                      # 应用主体
│   ├── api/                   # 教务客户端（按业务域拆分的 Mixin → Client）
│   ├── routes/                # HTTP 接口层（Flask 蓝图，统一挂载 /api）
│   ├── store/                 # SQLite 存储（绑定 / 订阅 / 成绩快照）
│   ├── wechat/                # access_token 与订阅消息推送
│   ├── tasks/                 # 定时任务（成绩检测与推送）
│   ├── docs.py                # OpenAPI + Swagger UI 自动生成
│   ├── school_config.py       # 学校配置管理器
│   ├── settings.py            # 路径 / .env 加载 / 共享常量
│   └── app.py                 # 应用工厂 create_app()
├── scripts/
│   ├── test_push.py           # 手动测试成绩推送
│   └── gen_api_docs.py        # 导出静态 API 文档
├── docs/                      # 生成物：静态 API 文档
├── data/                      # 运行时数据（SQLite、token 缓存、日志）
├── pyproject.toml             # 依赖声明（唯一来源）
├── uv.lock                    # 锁定的全依赖树
├── .python-version            # Python 版本
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

导入约定：`from zfjw.api import Client`、`from zfjw.store import PushStore`、
`from zfjw.wechat import send_grade_push`、`from zfjw.tasks import GRADE_TEMPLATE_ID`。

## 学校配置

配置位于 `config/schools_config.json`，采用 **模板 + 覆盖** 的写法：
7 所学校的 27 条 URL 路径基本一致，差异只在前缀与极个别 URL，故公共部分只写一份。

```jsonc
{
  "defaults": {
    "path_prefix": "",           // 默认无前缀，URL 直接挂在域名下
    "requires_captcha": true,
    "urls": { "login": "xtgl/login_slogin.html" /* … 共 27 个键 */ }
  },
  "schools": {
    "南昌职业大学": {              // 全用默认值：只需 3 个字段
      "school_code": "nvu", "base_url": "https://jwxt.nvu.edu.cn",
      "requires_captcha": false, "description": "南昌职业大学教务系统"
    },
    "九江学院": {                  // 路径多一段前缀
      "school_code": "jju", "base_url": "https://zhjw1.jju.edu.cn",
      "path_prefix": "jwglxt/", "description": "九江学院教务系统"
    },
    "西安邮电大学": {              // 个别 URL 例外
      "school_code": "xupt", "base_url": "http://www.zfjw.xupt.edu.cn",
      "path_prefix": "jwglxt/",
      "url_overrides": { "evaluate": "xspjgl/xspj_cxXspjIndex.html?doType=query&gnmkdm=N401605" },
      "description": "西安邮电大学教务系统"
    }
  }
}
```

- `url_overrides` 的值是**相对 `base_url` 的完整路径**，不再拼接 `path_prefix`。
- 新增学校通常只需填 `school_code` / `base_url` / `description`。
- 配置写错会在**服务启动时立即报错**（`SchoolConfigError`），不会等到调用接口才失败：
  键名拼写错误、缺少 `base_url` / `school_code`、`school_code` 重复、`path_prefix` 不以 `/` 结尾等。

### 已支持学校

| 学校 | 代码 | 验证码 | 路径前缀 |
|------|------|--------|---------|
| 九江学院 | jju | ✅ | `jwglxt/` |
| 南昌职业大学 | nvu | ❌ | 无（默认） |
| 南京工业大学 | njtech | ❌ | 无（默认） |
| 西安邮电大学 | xupt | ✅ | `jwglxt/`（评教 4 条例外） |
| 福建江夏学院 | fjjxu | ❌ | `jwglxt/`（评教 4 条例外） |
| 浙江农林大学暨阳学院 | zjyc | ✅ | 无（默认） |
| 广东工程职业技术学院 | gdep | ✅ | 无（默认） |

## 贡献

欢迎提交 Issue 或 PR。新增学校时请先在 `config/schools_config.json` 中补充配置并本地验证。

## 许可证

MIT © [drfccv/ZFJW-backend](LICENSE)

## 致谢

- [openschoolcn/zfn_api](https://github.com/openschoolcn/zfn_api) — 核心接口参考
- [Flask](https://flask.palletsprojects.com/) — Web 框架
