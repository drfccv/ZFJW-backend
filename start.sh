#!/bin/bash
# 生产环境启动脚本

# 设置项目目录
PROJECT_DIR="/path/to/your/ZFJW-backend"
cd $PROJECT_DIR

# 创建日志目录
mkdir -p logs

# 激活虚拟环境（如果使用）
# source venv/bin/activate

# 启动uWSGI
echo "启动ZFJW Backend API服务..."
uwsgi --ini uwsgi.ini

# 或者使用以下命令直接启动（不使用配置文件）
# uwsgi --http 0.0.0.0:5000 --module wsgi:application --processes 4 --threads 2 --master --vacuum --die-on-term
