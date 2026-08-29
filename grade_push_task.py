"""
grade_push_task.py — 定时成绩检测与推送
使用 APScheduler 定时检查成绩变化并推送订阅消息
"""
import json
import hashlib
import os
import time
import traceback
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from push_store import PushStore
from zfn_api import Client
from wechat_push import send_grade_push, send_account_abnormal

# 成绩推送模板 ID（模板 ID 不属于隐私）
GRADE_TEMPLATE_ID = "2KVe7leduIgeB6CinL8WwKq3OYx_Ddf3h81wG0yIaUE"
# 账号异常通知模板 ID
ACCOUNT_ABNORMAL_TEMPLATE_ID = "0Oc4TiORGaKYVGwwpS5TT7YqFLy0Z0JOFzwxrzYU134"

# gunicorn 多 worker 下防止重复启动调度器（配合 --preload 使用）
_scheduler_started = False


def _compute_hash(courses: list) -> str:
    """
    计算课程列表的哈希值，用于快照对比

    Args:
        courses: 课程列表

    Returns:
        MD5 哈希字符串
    """
    sorted_courses = sorted(
        courses,
        key=lambda c: (c.get("course_id", ""), str(c.get("grade", "")))
    )
    raw = json.dumps(sorted_courses, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _get_recent_year_terms():
    """
    获取需要查询的学年学期列表
    查询当前学年和上一学年，每个学年两个学期

    Returns:
        list[tuple]: [(year, term), ...]
    """
    now = datetime.now()
    current_year = now.year
    # 根据当前月份判断学年：9月之前属于上一学年
    if now.month < 9:
        current_academic_year = current_year - 1
    else:
        current_academic_year = current_year

    year_terms = []
    for y in [current_academic_year, current_academic_year - 1]:
        for t in [1, 2]:
            year_terms.append((y, t))
    return year_terms


def check_grades_and_push():
    """
    定时任务：检查成绩变化并推送订阅消息

    遍历所有活跃订阅用户，爬取最新成绩并与快照对比，
    如有新增课程则推送通知，cookies 失效则发送异常通知。
    """
    store = PushStore()
    subscriptions = store.get_all_active_subscriptions()

    total_users = len(subscriptions)
    total_pushed = 0
    total_abnormal = 0

    print(f"[GradePush] 开始成绩检测，活跃订阅用户数: {total_users}")

    for sub in subscriptions:
        openid = sub["openid"]
        # 两个模板 ID 已硬编码，不再从数据库读（防止订阅时存错 template_id 导致推送失败）
        grade_template_id = GRADE_TEMPLATE_ID

        try:
            # 获取绑定信息
            binding = store.get_binding(openid)
            if not binding:
                print(f"[GradePush] 用户 {openid} 未找到绑定信息，跳过")
                continue

            school_name = binding["school_name"]
            sid = binding["sid"]

            # 获取已有成绩快照
            old_snapshots = store.get_all_grade_snapshots_by_openid(openid)
            old_courses_map = {}  # key: (year, term) -> list of courses
            for snap in old_snapshots:
                try:
                    courses = json.loads(snap.get("grades", "[]"))
                    old_courses_map[(snap["year"], snap["term"])] = courses
                except (json.JSONDecodeError, TypeError):
                    old_courses_map[(snap["year"], snap["term"])] = []

            # 从绑定信息中读取 cookies
            user_cookies = binding.get("cookies", {}) or {}
            if not user_cookies:
                print(f"[GradePush] 用户 {openid} 未提供 cookies，跳过")
                continue

            stu = Client(
                cookies=user_cookies,
                school_name=school_name,
                timeout=30
            )

            year_terms = _get_recent_year_terms()
            has_new_grades = False
            has_any_success = False
            cookies_expired = False

            for year, term in year_terms:
                try:
                    result = stu.get_grade(year, term, school_name=school_name)

                    if result.get("code") == 1006:
                        # cookies 过期，标记并跳出
                        cookies_expired = True
                        print(f"[GradePush] 用户 {openid} cookies 已过期")
                        break

                    if result.get("code") != 1000:
                        print(f"[GradePush] 用户 {openid} 获取 {year}-{term} 成绩失败: {result.get('msg')}")
                        continue

                    has_any_success = True

                    grade_data = result.get("data", {})
                    new_courses = grade_data.get("courses", [])

                    if not new_courses:
                        continue

                    # 对比新旧成绩，找出新增课程
                    old_courses = old_courses_map.get((year, term), [])
                    old_course_keys = set()
                    for c in old_courses:
                        key = (c.get("course_id", ""), str(c.get("grade", "")))
                        old_course_keys.add(key)

                    def _normalize_grade(grade) -> str:
                        """将成绩标准化为字符串，非数字成绩（如"未评价"）转为"0" """
                        if grade is None:
                            return "0"
                        if isinstance(grade, (int, float)):
                            return str(grade)
                        if isinstance(grade, str):
                            try:
                                float(grade)
                                return grade
                            except (ValueError, TypeError):
                                return "0"
                        return "0"

                    new_added_courses = []
                    for c in new_courses:
                        key = (c.get("course_id", ""), str(c.get("grade", "")))
                        if key not in old_course_keys:
                            new_added_courses.append(c)

                    if new_added_courses:
                        has_new_grades = True
                        print(f"[GradePush] 用户 {openid} {year}-{term} 发现 {len(new_added_courses)} 门新课程")
                        for course in new_added_courses:
                            try:
                                score = _normalize_grade(course.get("grade"))
                                if score == "0" and str(course.get("grade", "")) != "0":
                                    print(f"[GradePush] 课程 {course.get('title', '')} 成绩为'未评价'，推送为0分")
                                send_grade_push(
                                    openid=openid,
                                    template_id=grade_template_id,
                                    course_name=course.get("title", ""),
                                    score=score,
                                    course_type=course.get("category", ""),
                                    credit=str(course.get("credit", ""))
                                )
                                total_pushed += 1
                            except Exception as push_err:
                                print(f"[GradePush] 推送失败: {push_err}")

                    # 更新快照（无论是否有新增，都更新为最新数据）
                    data_hash = _compute_hash(new_courses)
                    grades_json = json.dumps(new_courses, ensure_ascii=False)
                    store.save_grade_snapshot(openid, year, term, data_hash, grades_json)

                except Exception as api_err:
                    print(f"[GradePush] 用户 {openid} {year}-{term} 查询异常: {api_err}")
                    traceback.print_exc()

            # 如果 cookies 失效，发送异常通知并取消订阅
            if cookies_expired:
                try:
                    send_account_abnormal(
                        openid=openid,
                        template_id=ACCOUNT_ABNORMAL_TEMPLATE_ID,
                        status_text="登录过期",
                        sid=sid
                    )
                    store.delete_subscription(openid)
                    store.delete_binding(openid)
                    total_abnormal += 1
                    print(f"[GradePush] 用户 {openid} 已发送异常通知并解绑")
                except Exception as abn_err:
                    print(f"[GradePush] 异常通知发送失败: {abn_err}")
            elif not has_any_success:
                # 所有学年学期均查询失败（非 cookies 过期），如教务系统服务异常
                try:
                    send_account_abnormal(
                        openid=openid,
                        template_id=ACCOUNT_ABNORMAL_TEMPLATE_ID,
                        status_text="系统服务异常",
                        sid=sid
                    )
                    total_abnormal += 1
                    print(f"[GradePush] 用户 {openid} 教务系统服务异常，已发送通知")
                except Exception as abn_err:
                    print(f"[GradePush] 异常通知发送失败: {abn_err}")

        except Exception as user_err:
            print(f"[GradePush] 处理用户 {openid} 时出错: {user_err}")
            traceback.print_exc()

    print(
        f"[GradePush] 成绩检测完成 - "
        f"检查用户: {total_users}, 推送消息: {total_pushed}, 异常账号: {total_abnormal}"
    )


def init_scheduler(app):
    """
    初始化定时任务调度器（模块级标志防止 gunicorn 多 worker 重复启动）

    Args:
        app: Flask 应用实例
    """
    global _scheduler_started
    if _scheduler_started:
        return None
    _scheduler_started = True

    scheduler = BackgroundScheduler()

    # 添加定时任务：每 10 分钟执行一次，首次延迟 30 秒后执行
    from datetime import datetime as _dt, timedelta as _td
    start_time = _dt.now() + _td(seconds=30)

    scheduler.add_job(
        func=check_grades_and_push,
        trigger="interval",
        minutes=10,
        start_date=start_time,
        id="grade_push_job",
        name="成绩检测与推送",
    )

    try:
        scheduler.start()
        print(f"[GradePush] 定时任务调度器已启动 (pid={os.getpid()})，间隔 10 分钟，首次执行时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"[GradePush] 调度器启动失败: {e}")

    return scheduler
