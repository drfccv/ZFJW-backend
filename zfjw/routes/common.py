"""路由层共享依赖：错误处理、参数校验、客户端构造。

这些能力原先散落在 app.py 中并被各路由重复使用，现集中到此处。
"""
import functools
import traceback

from flask import jsonify

from zfjw import settings
from zfjw.api import Client
from zfjw.school_config import school_config_manager
from zfjw.store.push_store import PushStore

# 全局存储实例（进程内单例，与旧版行为一致）
push_store = PushStore()

# 运行参数，保持与旧版 app.py 完全一致
RASPISANIE = []
IGNORE_TYPE = []
DETAIL_CATEGORY_TYPE = []
TIMEOUT = settings.DEFAULT_TIMEOUT

# 用于区分“未传参”与“显式传 None”
_UNSET = object()


def handle_errors(func):
    """统一异常兜底装饰器。

    使用 functools.wraps 保留原函数的 __name__ / __doc__ / __wrapped__，
    这样接口文档生成器（zfjw.docs）才能取到真实的 docstring 与源码。
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"接口 {func.__name__} 发生错误: {str(e)}")
            traceback.print_exc()
            return jsonify({"code": 999, "msg": f"服务器内部错误: {str(e)}"})
    return wrapper


def build_client(cookies, base_url, school_name=_UNSET):
    """构造教务客户端。

    不传 school_name 时不写入该参数，保持 Client 的默认学校行为；
    显式传入（含 None）则原样透传，兼容历史调用差异。
    """
    kwargs = {
        "raspisanie": RASPISANIE,
        "ignore_type": IGNORE_TYPE,
        "detail_category_type": DETAIL_CATEGORY_TYPE,
        "timeout": TIMEOUT,
    }
    if school_name is not _UNSET:
        kwargs["school_name"] = school_name
    return Client(cookies=cookies, base_url=base_url, **kwargs)


def get_base_url_from_params(data):
    """从请求参数获取 base_url，支持通过 school_name 自动查找。

    返回 (base_url, error_response)：成功时 error_response 为 None；
    失败时 base_url 为 None，error_response 为可直接返回的响应对象。
    """
    base_url = data.get('base_url')
    school_name = data.get('school_name')

    # 校验参数：base_url 或 school_name 至少一个
    if not base_url and not school_name:
        return None, jsonify({"code": 400, "msg": "缺少 base_url 或 school_name 参数"})

    # 通过学校名称获取 base_url
    if not base_url and school_name:
        school_config = school_config_manager.get_school_config(school_name)
        if school_config:
            base_url = school_config.get('base_url')
            print(f"通过学校名称 '{school_name}' 获取到 base_url: {base_url}")
        else:
            return None, jsonify({"code": 400, "msg": f"未找到学校 '{school_name}' 的配置"})

    if not base_url:
        return None, jsonify({"code": 400, "msg": "未能获取到 base_url，请检查 school_name 是否正确或补充 base_url 参数"})

    return base_url, None
