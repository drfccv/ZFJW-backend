"""微信小程序相关能力（access_token、订阅消息推送）。"""
from zfjw.wechat.push import (
    send_account_abnormal,
    send_grade_push,
    send_subscribe_message,
)
from zfjw.wechat.token import get_access_token

__all__ = [
    "get_access_token",
    "send_subscribe_message",
    "send_grade_push",
    "send_account_abnormal",
]
