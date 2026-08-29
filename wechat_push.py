"""
wechat_push.py — 消息推送工具
封装微信订阅消息发送逻辑
"""
import requests
from wechat_token import get_access_token


def send_subscribe_message(openid: str, template_id: str, data: dict, page: str = ""):
    """
    发送微信订阅消息

    Args:
        openid: 接收者 openid
        template_id: 模板 ID
        data: 模板数据
        page: 点击跳转页面路径

    Returns:
        dict 或 None: 微信 API 响应
    """
    try:
        token = get_access_token()
        if not token:
            print("[WechatPush] 无法获取 access_token，消息发送失败")
            return None

        url = (
            "https://api.weixin.qq.com/cgi-bin/message/subscribe/send"
            f"?access_token={token}"
        )

        payload = {
            "touser": openid,
            "template_id": template_id,
            "page": page,
            "data": data
        }

        resp = requests.post(url, json=payload, timeout=10)
        result = resp.json()

        if result.get("errcode") == 0:
            pass
        else:
            print(f"[WechatPush] 发送失败: {result}")

        return result
    except Exception as e:
        print(f"[WechatPush] send_subscribe_message 出错: {e}")
        return None


def send_grade_push(openid: str, template_id: str, course_name: str,
                    score: str, course_type: str, credit: str):
    """
    发送成绩推送订阅消息

    Args:
        openid: 接收者 openid
        template_id: 成绩推送模板 ID
        course_name: 课程名称
        score: 考试分数
        course_type: 课程类型
        credit: 课程学分

    Returns:
        dict 或 None
    """
    data = {
        "thing11": {"value": str(course_name)},
        "number1": {"value": str(score)},
        "thing12": {"value": str(course_type)},
        "short_thing13": {"value": str(credit)}
    }

    return send_subscribe_message(
        openid=openid,
        template_id=template_id,
        data=data,
        page="/pages/grade/grade"
    )


def send_account_abnormal(openid: str, template_id: str,
                          status_text: str, sid: str):
    """
    发送账号异常通知订阅消息

    Args:
        openid: 接收者 openid
        template_id: 账号异常通知模板 ID
        status_text: 状态文本
        sid: 学号

    Returns:
        dict 或 None
    """
    import time as _time
    now_str = _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime())

    data = {
        "phrase1": {"value": str(status_text)},
        "time3": {"value": now_str},
        "thing6": {"value": f"学号: {sid}"}
    }

    return send_subscribe_message(
        openid=openid,
        template_id=template_id,
        data=data,
        page="/pages/login/login"
    )
