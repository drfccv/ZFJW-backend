"""学校配置管理器。

配置文件 `config/schools_config.json` 采用**模板 + 覆盖**的写法，避免每所学校
重复抄写同一套 URL：

    defaults.path_prefix       各校 URL 的公共前缀（如 "jwglxt/"）
    defaults.urls              公共 URL 模板（相对路径，不含前缀）
    defaults.requires_captcha  默认是否需要验证码
    defaults.parameters        默认扩展参数

    schools.<学校名>.path_prefix       覆盖默认前缀（"" 表示直接挂在域名下）
    schools.<学校名>.url_overrides     个别 URL 覆盖，值为相对 base_url 的完整路径
                                       （**不再**拼接 path_prefix）
    schools.<学校名>.requires_captcha  覆盖默认值
    schools.<学校名>.parameters        覆盖默认值

加载时会展开为完整的平铺结构（含 `urls` 全部绝对化前的相对路径），
因此 `/api/school/<name>` 等对外响应与旧版逐字节一致。

新增一所学校，通常只需填写 school_code / base_url / description 三个字段；
仅当前缀或个别 URL 与默认值不同时，才需要额外写 path_prefix / url_overrides。
"""
import json
import os
from typing import Dict, List, Optional
from urllib.parse import urljoin

from zfjw import settings


class SchoolConfigError(ValueError):
    """学校配置格式错误（配置写错时在启动阶段立即抛出，避免运行期静默失效）。"""


class SchoolConfigManager:
    """学校配置管理器：负责加载模板并展开成每校完整配置。"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or settings.SCHOOLS_CONFIG_FILE
        self.schools_config = self._load_config()

    # ── 加载与展开 ──────────────────────────────────────────────────
    def _load_config(self) -> Dict:
        """读取配置文件并展开为完整结构。"""
        try:
            if not os.path.exists(self.config_file):
                print(f"配置文件 {self.config_file} 不存在，返回空配置")
                return {}
            with open(self.config_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except json.JSONDecodeError as e:
            raise SchoolConfigError(f"配置文件 {self.config_file} 不是合法 JSON: {e}") from e
        except OSError as e:
            print(f"读取配置文件失败: {e}")
            return {}

        expanded = self._expand(raw)
        print(f"已加载 {len(expanded)} 所学校配置: {self.config_file}")
        return expanded

    def _expand(self, raw: Dict) -> Dict:
        """把「模板 + 覆盖」展开成每校完整配置。"""
        defaults = raw.get("defaults")
        schools = raw.get("schools")
        if not isinstance(defaults, dict) or not isinstance(schools, dict):
            raise SchoolConfigError(
                "配置格式要求顶层包含 defaults（默认模板）与 schools（学校列表）两个对象"
            )

        default_urls = defaults.get("urls")
        if not isinstance(default_urls, dict) or not default_urls:
            raise SchoolConfigError("defaults.urls 不能为空，需定义公共 URL 模板")

        default_prefix = defaults.get("path_prefix", "")
        self._check_prefix("defaults.path_prefix", default_prefix)
        default_captcha = defaults.get("requires_captcha", True)
        default_params = defaults.get("parameters", {})

        expanded: Dict[str, Dict] = {}
        seen_codes: Dict[str, str] = {}

        for name, item in schools.items():
            if not isinstance(item, dict):
                raise SchoolConfigError(f"学校 '{name}' 的配置必须是对象")

            base_url = item.get("base_url")
            if not base_url:
                raise SchoolConfigError(f"学校 '{name}' 缺少 base_url")

            code = item.get("school_code")
            if not code:
                raise SchoolConfigError(f"学校 '{name}' 缺少 school_code")
            if code in seen_codes:
                raise SchoolConfigError(
                    f"school_code '{code}' 重复：'{name}' 与 '{seen_codes[code]}'"
                )
            seen_codes[code] = name

            prefix = item.get("path_prefix", default_prefix)
            self._check_prefix(f"学校 '{name}' 的 path_prefix", prefix)

            # ① 先套公共模板 + 该校前缀
            urls = {key: prefix + path for key, path in default_urls.items()}

            # ② 再应用个别覆盖
            overrides = item.get("url_overrides", {})
            if not isinstance(overrides, dict):
                raise SchoolConfigError(f"学校 '{name}' 的 url_overrides 必须是对象")
            unknown = sorted(set(overrides) - set(default_urls))
            if unknown:
                raise SchoolConfigError(
                    f"学校 '{name}' 的 url_overrides 含未知 URL 键 {unknown}；"
                    f"可用键请见 defaults.urls（共 {len(default_urls)} 个）"
                )
            urls.update(overrides)

            expanded[name] = {
                "school_name": name,
                "school_code": code,
                "base_url": base_url,
                "requires_captcha": item.get("requires_captcha", default_captcha),
                "description": item.get("description", ""),
                "urls": urls,
                "parameters": item.get("parameters", default_params),
            }

        return expanded

    @staticmethod
    def _check_prefix(label: str, prefix) -> None:
        """前缀必须是空串或以 '/' 结尾的字符串。"""
        if not isinstance(prefix, str) or (prefix and not prefix.endswith("/")):
            raise SchoolConfigError(
                f"{label} 必须是空字符串或以 '/' 结尾的字符串，当前为 {prefix!r}"
            )

    # ── 查询接口 ────────────────────────────────────────────────────
    def get_schools_list(self) -> List[Dict]:
        """获取所有学校列表（不含 URL 明细，用于 /api/schools）。"""
        return [
            {
                "school_name": name,
                "school_code": config.get("school_code", ""),
                "base_url": config.get("base_url", ""),
                "requires_captcha": config.get("requires_captcha", True),
                "description": config.get("description", ""),
            }
            for name, config in self.schools_config.items()
        ]

    def get_school_config(self, school_name: str) -> Optional[Dict]:
        """根据学校名称获取完整配置（含 urls，用于 /api/school/<name>）。"""
        return self.schools_config.get(school_name)

    def get_school_url(self, school_name: str, url_type: str) -> Optional[str]:
        """获取学校某个功能的完整 URL。"""
        config = self.get_school_config(school_name)
        if not config:
            return None

        url_path = config.get("urls", {}).get(url_type)
        if not url_path:
            return None

        base_url = config.get("base_url", "")
        if not base_url.endswith("/"):
            base_url += "/"
        return urljoin(base_url, url_path)

    def get_base_url(self, school_name: str) -> str:
        """获取学校的 base_url。"""
        config = self.get_school_config(school_name)
        return config.get("base_url", "") if config else ""

    def requires_captcha(self, school_name: str) -> bool:
        """检查学校是否需要验证码（未配置的学校默认需要）。"""
        config = self.get_school_config(school_name)
        if not config:
            return True
        return config.get("requires_captcha", True)


# 全局单例，供各模块直接引用
school_config_manager = SchoolConfigManager()
