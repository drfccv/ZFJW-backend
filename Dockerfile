# 由 Dockerpacks 自动生成
# 本 Dockerfile 可能不能完全覆盖您的项目需求，若遇到问题请根据实际情况修改或询问客服

# 使用基于 alpine 的 python 官方镜像
FROM python:3-alpine

# 设置容器内的当前目录
WORKDIR /app

# 安装系统依赖（uWSGI需要编译工具）
RUN apk add --no-cache gcc musl-dev linux-headers

# 使用速度更快的国内镜像
RUN python3 -m pip config set global.trusted-host mirrors.cloud.tencent.com && \
    python3 -m pip config set global.index-url http://mirrors.cloud.tencent.com/pypi/simple

# 将 requirements.txt 复制到容器中
COPY requirements.txt requirements.txt

# 安装依赖
RUN python3 -m pip install -r requirements.txt

# 将所有文件拷贝到容器中（在 .dockerignore 中的文件除外）
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 创建非root用户
RUN addgroup -g 1000 www && \
    adduser -D -s /bin/sh -u 1000 -G www www

# 设置文件权限
RUN chown -R www:www /app

# 切换到非root用户
USER www

# 运行项目（生产环境使用uWSGI）
CMD ["uwsgi", "--ini", "uwsgi.ini"]

# 服务暴露的端口
EXPOSE 5000