# 📚 ZFJW-backend: 正方教务系统后端 API

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

一个使用 Flask 封装为 RESTful API 的正方教务系统后端服务，支持 **7 所高校** 教务数据查询，专为微信小程序和 Web 应用提供统一的数据接口。

## ✨ 功能特性

- 🔑 登录验证（密码 / 验证码 / Cookies）
- 👤 个人信息、📈 成绩、📅 考试、📄 课表、📊 学业生涯查询
- 🏢 空教室查询（校区、楼栋、时间段）
- 📝 一键评教（菜单、详情、保存、提交）
- ➕ 选课 / 退课
- 📩 成绩推送（绑定 openid、订阅、定时推送）
- 🏫 多校支持（通过 `schools_config.json` 配置，目前 7 所）

## 🚀 快速开始

### 环境要求
- Python 3.7+
- pip

### 安装与运行

```bash
git clone https://github.com/drfccv/ZFJW-backend.git
cd ZFJW-backend
pip install -r requirements.txt

# （可选）配置微信凭据，用于成绩推送
cp .env.example .env   # 然后编辑 .env 填入 APPID / APPSECRET

python app.py          # 服务默认运行在 http://localhost:5000
```

> 验证服务:`curl http://localhost:5000/api/health`
>
> 微信凭据（`APPID` / `APPSECRET`）通过环境变量或 `.env` 文件注入，请勿硬编码到代码中。未配置时仅成绩推送不可用。

### Docker 部署

先本地创建 `.env` 并填入微信凭据（`APPID` / `APPSECRET`）:

```bash
cp .env.example .env
# 编辑 .env:  APPID=你的AppID
#             APPSECRET=你的AppSecret（注意保密，不要提交）
```

**方式一：`docker run`**（用 `--env-file` 把 `.env` 注入容器）

```bash
docker build -t zfjw-backend .
docker run -p 5000:5000 --env-file .env zfjw-backend
```

**方式二：`docker compose`**（自动读取项目根目录的 `.env`）

```bash
docker compose up -d
```

> **启动方式**: 默认 `python app.py`（开发/轻量部署）；生产可改用 uWSGI 提升并发，仓库已含 `uwsgi.ini`，Compose 中通过 `command: uwsgi --ini uwsgi.ini` 覆盖即可。
>
> ⚠️ 未配置 `APPID` / `APPSECRET` 时，成绩推送功能不可用，其余接口不受影响。

## 📁 项目结构

```
ZFJW-backend/
├── app.py                # Flask 主程序（API 路由）
├── zfn_api.py            # 教务系统 API 核心
├── school_config.py      # 学校配置处理
├── schools_config.json   # 学校配置文件
├── wechat_token.py       # 微信 access_token 管理
├── wechat_push.py        # 微信订阅消息推送
├── push_store.py         # 学生绑定/订阅/成绩快照存储（SQLite）
├── grade_push_task.py    # 定时成绩检测与推送（APScheduler）
├── test_push.py          # 手动测试成绩推送
├── uwsgi.ini             # uWSGI 生产配置（可选）
├── requirements.txt      # Python 依赖
├── Dockerfile            # Docker 构建
├── docker-compose.yml    # Docker Compose
├── .env.example          # 环境变量模板
├── api.md                # API 接口文档
└── LICENSE
```

## 🔌 API 概览

完整接口清单见 [api.md](api.md)。主要接口:

- `POST /api/login`、`POST /api/login_with_kaptcha` — 登录
- `POST /api/info` — 个人信息
- `POST /api/grade`、`POST /api/grade_detail` — 成绩
- `POST /api/exam` — 考试安排
- `POST /api/schedule`、`POST /api/schedule_pdf` — 课表
- `POST /api/notifications` — 停补换课消息
- `POST /api/academia` — 学业生涯
- `POST /api/selected_courses` — 已选课程
- `POST /api/select_course`、`POST /api/drop_course` — 选课/退课
- `POST /api/classroom` — 空教室
- `POST /api/evaluate_menu`、`/api/evaluate_save`、`/api/evaluate_submit` — 评教
- `POST /api/bind_openid`、`/api/subscribe_grade_push` — 成绩推送绑定/订阅

> 认证采用 Session-based，数据格式为 JSON，Base URL 为 `http://localhost:5000/api`。

## ⚙️ 学校配置

- `schools_config.json` 按学校名称组织配置，包含 `base_url`、`school_code`、`requires_captcha`、`urls`、`parameters` 等。
- 新增学校时，参照已有条目添加即可（可参考 [openschoolcn/zfn_api](https://github.com/openschoolcn/zfn_api) 的接口约定）。

```json
{
  "九江学院": {
    "base_url": "https://zhjw1.jju.edu.cn",
    "school_name": "九江学院",
    "school_code": "jju",
    "requires_captcha": true,
    "description": "九江学院教务系统",
    "urls": {
      "login": "jwglxt/xtgl/login_slogin.html",
      "grade": "jwglxt/cjcx/cjcx_cxXsgrcj.html?doType=query&gnmkdm=N305005",
      "schedule": "jwglxt/kbcx/xskbcx_cxXsgrkb.html?gnmkdm=N2151"
    }
  }
}
```

### 已支持学校

| 学校 | 代码 | 验证码 |
|------|------|--------|
| 九江学院 | jju | ✅ |
| 南昌职业大学 | nvu | ❌ |
| 南京工业大学 | njtech | ❌ |
| 西安邮电大学 | xupt | ✅ |
| 福建江夏学院 | fjjxu | ❌ |
| 浙江农林大学暨阳学院 | zjyc | ✅ |
| 广东工程职业技术学院 | gdep | ✅ |

## 🤝 贡献

欢迎提交 PR 或 Issue。新功能、Bug 修复、新增学校配置、文档改进等均可。添加学校支持时，请先在 `schools_config.json` 中新增配置并本地验证，再提交 PR 并附上测试结果。

## ❓ 常见问题

- **登录失败？** 检查学号密码、学校配置、网络连接。
- **接口返回空？** 检查当前学期数据、学校系统状态、接口参数。
- **添加新学校？** 见上文「学校配置」。

## 📄 许可证

MIT © [drfccv/ZFJW-backend](LICENSE)

## 🙏 致谢

- [openschoolcn/zfn_api](https://github.com/openschoolcn/zfn_api) — 本项目核心教务系统接口参考
- [Flask](https://flask.palletsprojects.com/) — Web 框架

## 📞 联系

📧 27123587802@qq.com · 🐛 [Issues](https://github.com/drfccv/ZFJW-backend/issues)

---

⭐ 如果对你有帮助，请给个 Star！

