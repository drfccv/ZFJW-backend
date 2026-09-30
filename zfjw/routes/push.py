"""成绩推送订阅 接口。"""
from flask import Blueprint
from flask import jsonify
from flask import request

import os
import requests
from zfjw.routes.common import handle_errors
from zfjw.routes.common import push_store


bp = Blueprint("push", __name__)


@bp.route('/bind_openid', methods=['POST'])
@handle_errors
def bind_openid():
    """
    绑定 openid 接口
    用小程序 code 换取 openid，并保存绑定关系

    请求参数:
        code: 微信登录 code
        school_name: 学校名称
        sid: 学号
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})

    code = data.get('code')
    school_name = data.get('school_name')
    sid = data.get('sid')

    cookies = data.get('cookies')

    if not all([code, school_name, sid, cookies]):
        return jsonify({"code": 400, "msg": "参数不完整，需要 code, school_name, sid, cookies"})

    APPID = os.environ.get('APPID', '')
    APPSECRET = os.environ.get('APPSECRET', '')

    if not APPID or not APPSECRET:
        return jsonify({"code": 500, "msg": "服务器未配置微信凭据 APPID/APPSECRET，请通过环境变量设置"})

    wx_url = (
        "https://api.weixin.qq.com/sns/jscode2session"
        f"?appid={APPID}&secret={APPSECRET}&js_code={code}"
        "&grant_type=authorization_code"
    )

    try:
        wx_resp = requests.get(wx_url, timeout=10)
        wx_data = wx_resp.json()
        print(f"[BindOpenid] 微信 jscode2session 响应: {wx_data}")

        openid = wx_data.get('openid')
        if not openid:
            return jsonify({
                "code": 999,
                "msg": f"获取 openid 失败: {wx_data.get('errmsg', '未知错误')}"
            })

        push_store.save_binding(openid, school_name, sid, cookies)

        return jsonify({
            "code": 1000,
            "data": {"openid": openid}
        })
    except Exception as e:
        print(f"[BindOpenid] 请求微信接口出错: {e}")
        return jsonify({"code": 999, "msg": f"换取 openid 失败: {str(e)}"})

@bp.route('/subscribe_grade_push', methods=['POST'])
@handle_errors
def subscribe_grade_push():
    """
    订阅成绩推送接口

    请求参数:
        openid: 微信 openid
        school_name: 学校名称
        template_id: 模板 ID（已废弃，后端固定使用 GRADE_TEMPLATE_ID）
        subscribe_status: 订阅状态（accept/reject）
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})

    openid = data.get('openid')
    subscribe_status = data.get('subscribe_status', 'accept')
    cookies = data.get('cookies')
    school_name = data.get('school_name')
    sid = data.get('sid')

    if not all([openid, cookies]):
        return jsonify({"code": 400, "msg": "参数不完整，需要 openid, cookies"})

    # 检查或自动创建绑定
    binding = push_store.get_binding(openid)
    if not binding:
        # 如果没有绑定记录，尝试从请求参数创建
        if school_name and sid:
            push_store.save_binding(openid, school_name, sid, cookies)
            print(f"[Subscribe] 自动创建绑定: openid={openid}, school={school_name}, sid={sid}")
        else:
            return jsonify({"code": 400, "msg": "未找到绑定记录且未提供 school_name/sid，请先调用 bind_openid 或补全参数"})
    else:
        # 有绑定记录，刷新 cookies
        push_store.save_binding(openid, binding["school_name"], binding["sid"], cookies)

    # 固定使用成绩推送模板 ID，忽略前端传入的 template_id
    from zfjw.tasks import GRADE_TEMPLATE_ID
    push_store.save_subscription(openid, GRADE_TEMPLATE_ID, subscribe_status)

    return jsonify({"code": 1000, "msg": "订阅成功"})

@bp.route('/unsubscribe_grade_push', methods=['POST'])
@handle_errors
def unsubscribe_grade_push():
    """
    取消成绩推送订阅接口

    请求参数:
        openid: 微信 openid
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})

    openid = data.get('openid')

    if not openid:
        return jsonify({"code": 400, "msg": "参数不完整，需要 openid"})

    push_store.delete_subscription(openid)
    push_store.delete_binding(openid)

    return jsonify({"code": 1000, "msg": "已取消订阅"})

@bp.route('/grade_push_status', methods=['GET', 'POST'])
@handle_errors
def grade_push_status():
    """
    查询成绩推送状态接口

    请求参数（query string 或 JSON body）:
        openid: 微信 openid
    """
    if request.method == 'POST':
        data = request.json
        openid = data.get('openid') if data else None
    else:
        openid = request.args.get('openid')

    if not openid:
        return jsonify({"code": 400, "msg": "参数不完整，需要 openid"})

    # 查询订阅状态
    subscription = push_store.get_subscription(openid)
    subscribed = subscription is not None and subscription.get('status') == 'accept'

    # 查询成绩快照
    snapshots = push_store.get_all_grade_snapshots_by_openid(openid)
    grade_snapshots = [
        {
            "year": s["year"],
            "term": s["term"],
            "update_time": s["update_time"]
        }
        for s in snapshots
    ]

    return jsonify({
        "code": 1000,
        "data": {
            "subscribed": subscribed,
            "grade_snapshots": grade_snapshots
        }
    })
