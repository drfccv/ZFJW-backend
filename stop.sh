#!/bin/bash
# 停止uWSGI服务脚本

echo "停止ZFJW Backend API服务..."

# 通过PID文件停止
if [ -f /tmp/uwsgi.pid ]; then
    PID=$(cat /tmp/uwsgi.pid)
    echo "发现PID文件，正在停止进程 $PID"
    kill -TERM $PID
    sleep 2
    
    # 检查进程是否已停止
    if kill -0 $PID 2>/dev/null; then
        echo "强制停止进程..."
        kill -KILL $PID
    fi
    
    rm -f /tmp/uwsgi.pid
    echo "服务已停止"
else
    echo "未找到PID文件，尝试通过进程名停止..."
    pkill -f "uwsgi.*wsgi:application"
    echo "停止命令已发送"
fi
