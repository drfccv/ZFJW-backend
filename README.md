# ZFJW-backend: 微信小程序后端API

本项目基于 zfn_api，使用 Flask 封装为 RESTful API，适配微信小程序调用。

## 主要功能
- 登录（自动识别验证码）
- 个人信息查询
- 成绩查询
- 考试信息查询
- 课表查询及 PDF 导出
- 学业生涯数据及 PDF 导出
- 停补换课消息
- 查询已选课程
- 获取选课板块课列表、选课、退课
- 空教室查询

## 快速开始
1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   pip install flask flask-cors
   ```
2. 运行后端服务：
   ```bash
   python app.py
   ```
3. 微信小程序通过 HTTP(S) 访问本服务。

## 目录结构
- app.py         # Flask 主程序
- zfn_api.py     # 教务API核心（需从 zfn_api 项目复制）
- requirements.txt

## 注意事项
- 需将 zfn_api.py 复制到本项目根目录。
- 如需自定义参数或适配不同学校，请参考 zfn_api.py 注释。
