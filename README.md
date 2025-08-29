# 📚 ZFJW-backend: 微信小程序教务系统后端API

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

一个基于 `zfn_api` 的教务系统后端服务，使用 Flask 封装为 RESTful API，专为微信小程序端提供数据接口。

## ✨ 特性

- 🔐 **安全认证**: 支持教务系统登录验证
- 📊 **数据查询**: 提供个人信息、成绩、考试等多维度数据
- 🏫 **多校支持**: 通过配置文件支持多所学校
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

### 🚧 开发中功能
- 📄 课表查询及 PDF 导出
- 📊 学业生涯数据及 PDF 导出
- ➕ 选课功能（选课、退课）
- 🏢 空教室查询

## 🚀 快速开始

### 环境要求
- Python 3.7+
- pip (Python 包管理器)

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/your-username/ZFJW-backend.git
   cd ZFJW-backend
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置学校信息**
   ```bash
   # 编辑 school_config.json 文件，添加你的学校配置
   cp school_config.example.json school_config.json
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
├── school_config.json    # 学校配置文件
├── school_config.py      # 学校配置处理模块
└── requirements.txt       # Python 依赖包
```

## 🔌 API 文档

本项目提供完整的 RESTful API 接口，支持用户认证、数据查询等功能。

**📖 完整 API 文档请查看：[API 文档](docs/api.md)**

### 快速预览
- **Base URL**: `http://localhost:5000/api`
- **认证方式**: Session-based  
- **数据格式**: JSON
- **主要接口**: 登录认证、个人信息、成绩查询、课表查询、考试安排等

## ⚙️ 配置说明

### school_config.json 示例

```json
{
  "school_name": "示例大学",
  "base_url": "http://jwxt.example.edu.cn",
  "login_url": "/jsxsd/xk/LoginToXk",
  "encoding": "gbk",
  "timeout": 30
}
```

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

如果你的学校尚未支持，欢迎提交 `school_config.json` 配置：

1. 复制 `school_config.example.json`
2. 填写你学校的具体参数
3. 测试功能是否正常
4. 提交 PR 并注明学校名称

## 📝 开发日志

- **v1.0.0** (2024-01-01)
  - 基础功能实现
  - 支持登录、成绩查询
  
- **v1.1.0** (2024-02-01)
  - 添加课表查询
  - 优化错误处理

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

- 📧 Email: your-email@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/ZFJW-backend/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/your-username/ZFJW-backend/discussions)

---

⭐ 如果这个项目对你有帮助，请给我们一个 Star！

