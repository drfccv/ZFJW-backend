# 使用基于 alpine 的 python 官方镜像（版本与 pyproject.toml 的 requires-python 一致）
FROM python:3.12-alpine

# 引入官方 uv 二进制，按 uv.lock 精确安装依赖
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# uv 运行行为：
#   UV_COMPILE_BYTECODE  安装时预编译字节码，加快容器启动
#   UV_LINK_MODE=copy    容器内无法硬链接缓存，改为复制（消除告警）
#   UV_PYTHON_DOWNLOADS  只使用镜像自带的 Python，不额外下载
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# 先只拷贝依赖清单再安装，利用 Docker 层缓存：
# 只要依赖没变，改动业务代码时不会重新安装依赖
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

# 拷贝项目其余文件（.dockerignore 中排除的除外）
COPY . .

# 让容器内直接使用虚拟环境中的 python
ENV PATH="/app/.venv/bin:$PATH"

# 创建日志目录、非 root 用户并移交属主
RUN mkdir -p logs && \
    addgroup -g 1000 www && \
    adduser -D -s /bin/sh -u 1000 -G www www && \
    chown -R www:www /app

USER www

EXPOSE 5000

# 默认启动方式：直接运行 Flask 应用（开发 / 轻量部署）
CMD ["python", "app.py"]

# 说明：本项目依赖均提供 musllinux 预编译 wheel（含 lxml），无需编译工具，故未安装 gcc。
# 若日后引入需要编译的包导致构建失败，取消下面一行的注释即可：
# RUN apk add --no-cache gcc musl-dev linux-headers
#
# 若需要更高并发，可改用 gunicorn（先加进 pyproject.toml 依赖，再替换上面的 CMD）：
# CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "app:app"]
