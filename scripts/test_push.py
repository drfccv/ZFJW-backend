"""手动测试成绩推送 / 账号异常通知。

⚠️ 请勿在此文件中填写真实 openid / sid，以免隐私信息被提交。
   真实值仅需在本地测试时临时填入，用完务必还原为占位符。

用法（在项目根目录执行）：
    python -m scripts.test_push
"""
from zfjw.tasks.grade_push import ACCOUNT_ABNORMAL_TEMPLATE_ID, GRADE_TEMPLATE_ID
from zfjw.wechat.push import send_account_abnormal, send_grade_push

if __name__ == '__main__':
    # ⚠️ 隐私信息（openid / sid）请从 bindings 表查询后临时填入，用完还原
    # 查询示例：sqlite3 data/push_data.db "SELECT openid, sid FROM bindings;"
    OPENID = "oXXXXXXXXXXXXXX"  # 你的 openid（从 bindings 表查）
    SID = "20XXXXXXXXX"         # 你的学号（从 bindings 表查）

    print("=" * 50)
    print("测试成绩推送...")
    result = send_grade_push(
        openid=OPENID,
        template_id=GRADE_TEMPLATE_ID,
        course_name="测试课程",
        score="0",
        course_type="必修",
        credit="4.0",
    )
    print(f"成绩推送结果: {result}")

    print("=" * 50)
    print("测试账号异常通知...")
    result2 = send_account_abnormal(
        openid=OPENID,
        template_id=ACCOUNT_ABNORMAL_TEMPLATE_ID,
        status_text="登录过期",
        sid=SID,
    )
    print(f"异常通知结果: {result2}")
    print("=" * 50)
