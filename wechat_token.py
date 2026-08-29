"""
wechat_token.py — access_token 管理器
负责获取和缓存微信 access_token
"""
import os
import json
import time
import requests


# 加载 .env 文件（若存在），用于注入 APPID / APPSECRET 等敏感凭据
def _load_dotenv(path: str = ".env"):
    """轻量加载 .env 文件到 os.environ（不额外依赖 python-dotenv）"""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

_load_dotenv()

# 微信小程序配置
# 重要：出于安全考虑，此处不再内置任何凭据。
# AppID / AppSecret 必须通过环境变量 APPID / APPSECRET 提供（参考 .env.example）。
_DEFAULT_APPID = os.environ.get("APPID", "")
_DEFAULT_APPSECRET = os.environ.get("APPSECRET", "")

# access_token 缓存文件路径（基于本文件目录，确保 gunicorn 多 worker 下路径一致）
_TOKEN_CACHE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data", "access_token.json"
)


def _ensure_cache_dir():
    """确保缓存目录存在"""
    cache_dir = os.path.dirname(_TOKEN_CACHE_FILE)
    if cache_dir and not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)


def _read_cached_token():
    """
    从缓存文件读取 access_token

    Returns:
        str 或 None
    """
    try:
        if not os.path.exists(_TOKEN_CACHE_FILE):
            return None
        with open(_TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        access_token = data.get("access_token")
        expires_at = data.get("expires_at", 0)
        now = int(time.time())
        # 提前 200 秒刷新，确保 token 不过期（微信 token 有效期 7200 秒）
        if access_token and now < expires_at - 200:
            return access_token
        else:
            print(f"[WechatToken] 缓存 token 已过期")
            return None
    except Exception as e:
        print(f"[WechatToken] 读取缓存文件出错: {e}")
        return None


def _write_cached_token(access_token: str, expires_in: int):
    """
    将 access_token 写入缓存文件

    Args:
        access_token: 微信 access_token
        expires_in: 有效时间（秒）
    """
    try:
        _ensure_cache_dir()
        now = int(time.time())
        data = {
            "access_token": access_token,
            "expires_at": now + expires_in,
            "update_time": now
        }
        with open(_TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        print(f"[WechatToken] 写入缓存文件出错: {e}")


def get_access_token():
    """
    获取有效的 access_token
    优先从缓存读取，缓存过期则调用微信 API 获取新的

    Returns:
        str 或 None
    """
    # 先从缓存读取
    cached = _read_cached_token()
    if cached:
        return cached

    # 缓存无效，调用微信 API 获取
    appid = os.environ.get("APPID", _DEFAULT_APPID)
    appsecret = os.environ.get("APPSECRET", _DEFAULT_APPSECRET)

    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={appid}&secret={appsecret}"
    )

    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if "access_token" in data:
            access_token = data["access_token"]
            expires_in = data.get("expires_in", 7200)
            _write_cached_token(access_token, expires_in)
            return access_token
        else:
            print(f"[WechatToken] 获取 access_token 失败: {data}")
            return None
    except Exception as e:
        print(f"[WechatToken] 获取 access_token 出错: {e}")
        return None
