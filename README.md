# 📚 ZFJW-backend: 正方教务系统后端API

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)
![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)

一个基于 `zfn_api` 的正方教务系统后端服务，使用 Flask 封装为 RESTful API，支持 **6所高校** 教务数据查询，专为微信小程序和Web应用提供统一的数据接口。

## ✨ 特性

- 🔐 **安全认证**: 支持教务系统登录验证
- 📊 **数据查询**: 提供个人信息、成绩、考试等多维度数据
- 🏫 **多校支持**: 通过配置文件支持6所高校，持续扩展中
- 🚀 **轻量级**: 基于 Flask 框架，部署简单
- 📱 **小程序适配**: 专为微信小程序优化的 API 设计

## 🔧 主要功能

### ✅ 已实现功能
- 🔑 用户登录验证
- 👤 个人信息查询
- 📈 成绩查询与统计
- 📅 考试安排查询
- 📢 停补换课消息推送
- 📚 已选课程查询
- 📄 课表查询
- ➕ 选课功能（目前仅实现查询）
- 🏢 空教室查询（支持校区、楼栋、时间段筛选）

### 🚧 开发中功能
- 📊 学业生涯数据及 PDF 导出
- ➕ 选课功能（选课、退课操作）

## 🚀 快速开始

### 环境要求
- Python 3.7+
- pip (Python 包管理器)

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/drfccv/ZFJW-backend.git
   cd ZFJW-backend
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置学校信息**
   ```bash
   # 项目已包含主要学校配置，可直接使用
   # 如需添加新学校，请编辑 schools_config.json 文件
   ```

4. **启动服务**
   ```bash
   python app.py
   ```

5. **测试接口**
   ```bash
   # 服务默认运行在 http://localhost:5000
   curl http://localhost:5000/api/health
   ```

### Docker 部署（可选）

```bash
# 构建镜像
docker build -t zfjw-backend .

# 运行容器
docker run -p 5000:5000 zfjw-backend
```

## 📁 项目结构

```
ZFJW-backend/
├── app.py                 # Flask 主应用程序
├── zfn_api.py            # 教务系统 API 核心模块
├── schools_config.json   # 学校配置文件
├── school_config.py      # 学校配置处理模块
├── requirements.txt      # Python 依赖包
├── Dockerfile           # Docker 构建文件
├── docker-compose.yml   # Docker Compose 配置
├── uwsgi.ini           # uWSGI 配置文件
├── wsgi.py             # WSGI 入口文件
├── start.sh            # 启动脚本
├── stop.sh             # 停止脚本
└── api.md              # API 接口文档
```

## 🔌 API 文档

本项目提供完整的 RESTful API 接口，支持用户认证、数据查询等功能。

**📖 完整 API 文档请查看：[API 文档](api.md)**

### 快速预览
- **Base URL**: `http://localhost:5000/api`
- **认证方式**: Session-based  
- **数据格式**: JSON
- **主要接口**: 登录认证、个人信息、成绩查询、课表查询、考试安排等

## ⚙️ 配置说明

### schools_config.json 示例

```json
{
  "九江学院": {
    "base_url": "https://zhjw1.jju.edu.cn",
    "school_code": "jju",
    "description": "九江学院教务系统",
    "requires_captcha": true
  },
  "南昌职业大学": {
    "base_url": "https://jwxt.nvu.edu.cn",
    "school_code": "nvu", 
    "description": "南昌职业大学教务系统",
    "requires_captcha": false
  },
  "南京工业大学": {
    "base_url": "https://jwgl.njtech.edu.cn",
    "school_code": "njtech",
    "description": "南京工业大学教务系统",
    "requires_captcha": false
  }
}
```

> 📝 **说明**: 配置文件包含学校基本信息、URL路径、参数映射等详细配置，支持灵活的多校适配。

### 支持的学校列表

| 学校名称 | 学校代码 | 验证码要求 | 一键评教 | 状态 |
|---------|---------|-----------|-----------|------|
| 九江学院 | jju | ✅ | ✅ | ✅ 已支持 |
| 南昌职业大学 | nvu | ❌ | ❌ | ✅ 已支持 |
| 南京工业大学 | njtech | ❌ | ❌ | ✅ 已支持 |
| 西安邮电大学 | xupt | ✅ | ❌ | ✅ 已支持 |
| 浙江农林大学暨阳学院 | zafu | ✅ | ❌ | ✅ 已支持 |
| 广东工程职业技术学院 | gpc | ✅ | ❌ | ✅ 已支持 |

> 💡 **提示**: 如需添加新学校支持，请参考贡献指南提交配置。目前已支持 **6所** 高校教务系统。

## 🤝 贡献指南

我们欢迎任何形式的贡献！

### 如何贡献

1. **Fork 本仓库**
2. **创建特性分支** (`git checkout -b feature/AmazingFeature`)
3. **提交更改** (`git commit -m 'Add some AmazingFeature'`)
4. **推送到分支** (`git push origin feature/AmazingFeature`)
5. **打开 Pull Request**

### 贡献类型

- 🐛 **Bug 修复**
- ✨ **新功能开发**
- 📝 **文档改进**
- 🏫 **新学校配置**
- 🧪 **测试用例**

### 学校配置贡献

如果你的学校尚未支持，欢迎提交 `schools_config.json` 配置：

1. 在 `schools_config.json` 中添加你学校的配置
2. 填写学校的具体参数（base_url、编码、验证码要求等）
3. 本地测试功能是否正常
4. 提交 PR 并注明学校名称和测试结果
5. 提供学校教务系统的访问地址和登录方式


## ❓ 常见问题

### Q: 为什么登录失败？
A: 请检查：
- 学号密码是否正确
- 学校配置是否正确
- 网络连接是否正常

### Q: 如何添加新学校支持？
A: 请参考贡献指南中的学校配置部分。

### Q: 接口返回数据为空？
A: 可能原因：
- 当前学期没有相关数据
- 学校系统维护中
- 接口参数不正确

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) - 详细信息请查看 LICENSE 文件。

## 🙏 致谢

- [zfn_api](https://github.com/zfn_api/zfn_api) - 核心教务系统接口
- [Flask](https://flask.palletsprojects.com/) - Web 框架
- 所有贡献者和用户的支持

## 📞 联系我们

- 📧 Email: 27123587802@qq.com
- 🐛 Issues: [GitHub Issues](https://github.com/drfccv/ZFJW-backend/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/drfccv/ZFJW-backend/discussions)

---

⭐ 如果这个项目对你有帮助，请给我们一个 Star！

