"""全局路径、环境变量加载与共享常量。

本模块集中管理所有模块都需要的基础配置，避免各文件重复实现 .env 解析
或各自硬编码相对路径。
"""
import os


def _load_dotenv(path: str = None) -> None:
    """轻量加载 .env 文件到 os.environ（不额外依赖 python-dotenv）。

    仅当同名环境变量尚未设置时才写入，已存在的环境变量优先级更高。
    """
    if path is None:
        path = os.path.join(ROOT_DIR, ".env")
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


# ── 路径 ────────────────────────────────────────────────────────────────
# 项目根目录（zfjw 包的上一级）
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(ROOT_DIR, "config")
DATA_DIR = os.path.join(ROOT_DIR, "data")

SCHOOLS_CONFIG_FILE = os.path.join(CONFIG_DIR, "schools_config.json")

# 加载 .env（在路径常量之后，便于 .env 覆盖默认值）
_load_dotenv()


def ensure_data_dir() -> str:
    """确保 data/ 目录存在并返回其路径。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    return DATA_DIR


# ── 业务默认值 ──────────────────────────────────────────────────────────
DEFAULT_SCHOOL_NAME = "九江学院"
DEFAULT_TIMEOUT = 60

# 上课节次时间表，用于课表展示
RASPISANIE = [
    ["8:00", "8:40"],
    ["8:45", "9:25"],
    ["9:30", "10:10"],
    ["10:30", "11:10"],
    ["11:15", "11:55"],
    ["14:30", "15:10"],
    ["15:15", "15:55"],
    ["16:05", "16:45"],
    ["16:50", "17:30"],
    ["18:40", "19:20"],
    ["19:25", "20:05"],
    ["20:10", "20:50"],
    ["20:55", "21:35"],
]
