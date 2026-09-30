"""教务系统客户端：按业务域拆分的 Mixin 组合成 Client。

调用方式：`from zfjw.api import Client`
"""
from zfjw.api.base import BaseMixin
from zfjw.api.classroom import ClassroomMixin
from zfjw.api.course import CourseMixin
from zfjw.api.evaluate import EvaluateMixin
from zfjw.api.exam import ExamMixin
from zfjw.api.grade import GradeMixin
from zfjw.api.helpers import HelpersMixin
from zfjw.api.info import InfoMixin
from zfjw.api.login import LoginMixin
from zfjw.api.schedule import ScheduleMixin


class Client(
    LoginMixin,
    InfoMixin,
    GradeMixin,
    ExamMixin,
    ScheduleMixin,
    CourseMixin,
    EvaluateMixin,
    ClassroomMixin,
    HelpersMixin,
    BaseMixin,
):
    """正方教务系统客户端。

    由各业务域 Mixin 组合而成，`__init__` 与 URL 构建由 `BaseMixin` 提供。
    """


__all__ = ["Client"]
