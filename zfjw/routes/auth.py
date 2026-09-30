"""登录与验证码 接口。"""
from flask import Blueprint
from flask import jsonify
from flask import request

import traceback
from zfjw.routes.common import build_client
from zfjw.routes.common import get_base_url_from_params
from zfjw.routes.common import handle_errors
from zfjw.school_config import school_config_manager


bp = Blueprint("auth", __name__)


@bp.route('/login', methods=['POST'])
@handle_errors
def login():
    """密码登录（自动识别是否需要验证码）

    若学校需要验证码，返回 `code=1001` 与验证码图片，需再调用
    `/api/login_with_kaptcha` 完成登录；否则直接返回 `code=1000` 与 cookies。
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    print(f"收到登录请求: {data}")
    
    sid = data.get('sid')
    password = data.get('password')
    base_url = data.get('base_url')
    school_name = data.get('school_name', '九江学院')  # 新增学校名称参数
    
    # 校验参数：sid、password 必须有，base_url 或 school_name 至少一个
    if not sid or not password or (not base_url and not school_name):
        return jsonify({"code": 400, "msg": "参数不完整，需要 sid, password 和 (base_url 或 school_name)"})

    # 通过学校名称获取 base_url（school_name 缺省为“九江学院”，与旧版一致）
    base_url, error_response = get_base_url_from_params({**data, 'school_name': school_name})
    if error_response:
        return error_response

    # 检查学校是否需要验证码
    requires_captcha = school_config_manager.requires_captcha(school_name)
    if requires_captcha:
        print(f"学校 '{school_name}' 需要验证码，直接返回验证码获取提示")
        # 获取验证码进行登录验证
        try:
            stu = build_client({}, base_url, school_name)
            lgn = stu.login(sid, password)
            return jsonify(lgn)
        except Exception as e:
            print(f"验证码登录过程中发生异常: {str(e)}")
            traceback.print_exc()
            return jsonify({
                "code": 999,
                "msg": f"登录过程发生异常: {str(e)}"
            })
      # 创建Client实例
    try:
        stu = build_client({}, base_url, school_name)
        
        # 执行登录操作
        lgn = stu.login(sid, password)
        print(f"登录结果: {lgn}")
        
        return jsonify(lgn)
        
    except Exception as e:
        print(f"登录过程中发生异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "code": 999,
            "msg": f"登录过程发生异常: {str(e)}"
        })

@bp.route('/login_with_kaptcha', methods=['POST'])
@handle_errors
def login_with_kaptcha():
    """提交验证码完成登录

    使用 `/api/login` 返回的 csrf_token / cookies / modulus / exponent
    以及用户识别的验证码，完成登录并返回 cookies。
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    print(f"收到验证码登录请求: {data}")
    
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    try:
        stu = build_client({}, base_url)
        
        # 准备验证码登录参数，排除base_url
        login_params = {k: v for k, v in data.items() if k != 'base_url'}
        
        ret = stu.login_with_kaptcha(**login_params)
        
        print(f"验证码登录结果: {ret}")
        return jsonify(ret)
        
    except Exception as e:
        print(f"验证码登录过程中发生异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "code": 999,
            "msg": f"验证码登录过程发生异常: {str(e)}"
        })

# Client 内部错误文案与 /api/get_captcha 历史文案存在差异，
# 为保持对外响应完全不变，这里做一次映射。
_CAPTCHA_LEGACY_MSG = {
    "登录URL未设置，请检查base_url配置": "学校配置不完整，无法获取登录或验证码URL",
    "验证码URL未设置，请检查base_url配置": "学校配置不完整，无法获取登录或验证码URL",
    "公钥URL未设置，请检查base_url配置": "学校配置不完整，无法获取公钥URL",
}


def _legacy_captcha_error(err):
    """把 prepare_captcha_login 的错误映射回 /api/get_captcha 的历史文案。"""
    msg = err.get("msg", "")
    if msg in _CAPTCHA_LEGACY_MSG:
        msg = _CAPTCHA_LEGACY_MSG[msg]
    elif msg.startswith("登录页面访问失败，状态码:"):
        msg = msg.replace("登录页面访问失败，", "无法访问登录页面，", 1)
    return {"code": err.get("code", 2333), "msg": msg}


@bp.route('/get_captcha', methods=['POST'])
@handle_errors
def get_captcha():
    """获取登录验证码图片

    返回 base64 图片及后续登录所需的 csrf_token / 公钥 / cookies。
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    print(f"收到获取验证码请求: {data}")
    
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response

    school_name = data.get('school_name')

    try:
        stu = build_client({}, base_url, school_name)

        # 复用 Client 的登录前置流程；force_captcha=True 保持“总是返回验证码图片”的旧行为
        prep, err = stu.prepare_captcha_login(force_captcha=True)
        if err:
            return jsonify(_legacy_captcha_error(err))

        result = {
            "code": 1001,
            "msg": "获取验证码成功",
            "data": {
                "kaptcha": prep["kaptcha_pic"],
                "cookies": dict(stu.sess.cookies),
                "csrf_token": prep["csrf_token"],
                "modulus": prep["modulus"],
                "exponent": prep["exponent"]
            }
        }

        print(f"获取验证码结果: 验证码大小 {prep['kaptcha_size']} bytes")
        return jsonify(result)

    except Exception as e:
        print(f"获取验证码过程中发生异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "code": 999,
            "msg": f"获取验证码过程发生异常: {str(e)}"
        })
