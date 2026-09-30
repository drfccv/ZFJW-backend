"""ZFJW Backend —— 正方教务系统 API 服务。

包结构：
    zfjw.api      教务系统客户端（按业务域拆分的 Mixin）
    zfjw.routes   Flask 蓝图（HTTP 接口层）
    zfjw.store    SQLite 数据存储
    zfjw.wechat   微信小程序 access_token 与订阅消息推送
    zfjw.tasks    定时任务（成绩检测推送）
"""

__version__ = "2.0.0"
