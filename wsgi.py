#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI入口文件
用于生产环境部署
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入Flask应用
from app import app

# 设置生产环境配置
app.config['ENV'] = 'production'
app.config['DEBUG'] = False

# uWSGI应用对象
application = app

if __name__ == "__main__":
    # 直接运行时使用开发服务器
    app.run(host='0.0.0.0', port=5000, debug=False)
