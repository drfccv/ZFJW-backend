"""通用解析与格式化工具。"""
import binascii
import re
import unicodedata
import rsa


class HelpersMixin:
    @classmethod
    def encrypt_password(cls, pwd, n, e):
        """对密码base64编码"""
        message = str(pwd).encode()
        rsa_n = binascii.b2a_hex(binascii.a2b_base64(n))
        rsa_e = binascii.b2a_hex(binascii.a2b_base64(e))
        key = rsa.PublicKey(int(rsa_n, 16), int(rsa_e, 16))
        encropy_pwd = rsa.encrypt(message, key)
        result = binascii.b2a_base64(encropy_pwd)
        return result

    @classmethod
    def parse_int(cls, digits):
        if not digits:
            return None
        if not digits.isdigit():
            return digits
        return int(digits)

    @classmethod
    def align_floats(cls, floats):
        if not floats:
            return None
        if floats == "无":
            return "0.0"
        # 处理非数字字符串（如"未评价"）
        try:
            return format(float(floats), ".1f")
        except (ValueError, TypeError):
            # 如果无法转换为浮点数，返回原始字符串
            return str(floats)

    @classmethod
    def display_course_time(cls, sessions):
        if not sessions:
            return None
        args = re.findall(r"(\d+)", sessions)
        start_time = cls.raspisanie[int(args[0]) + 1][0]
        end_time = cls.raspisanie[int(args[0]) + 1][1]
        return f"{start_time}~{end_time}"

    @classmethod
    def list_sessions(cls, sessions):
        if not sessions:
            return None
        args = re.findall(r"(\d+)", sessions)
        return [n for n in range(int(args[0]), int(args[1]) + 1)]

    @classmethod
    def list_weeks(cls, weeks):
        """返回课程所含周列表"""
        if not weeks:
            return None
        args = re.findall(r"[^,]+", weeks)
        week_list = []
        for item in args:
            if "-" in item:
                weeks_pair = re.findall(r"(\d+)", item)
                if len(weeks_pair) != 2:
                    continue
                if "单" in item:
                    for i in range(int(weeks_pair[0]), int(weeks_pair[1]) + 1):
                        if i % 2 == 1:
                            week_list.append(i)
                elif "双" in item:
                    for i in range(int(weeks_pair[0]), int(weeks_pair[1]) + 1):
                        if i % 2 == 0:
                            week_list.append(i)
                else:
                    for i in range(int(weeks_pair[0]), int(weeks_pair[1]) + 1):
                        week_list.append(i)
            else:
                week_num = re.findall(r"(\d+)", item)
                if len(week_num) == 1:
                    week_list.append(int(week_num[0]))
        return week_list

    @classmethod
    def get_academia_statistics(cls, display_statistics):
        display_statistics = "".join(display_statistics.split())
        gpa_list = re.findall(r"([0-9]{1,}[.][0-9]*)", display_statistics)
        if len(gpa_list) == 0 or not cls.is_number(gpa_list[0]):
            gpa = None
        else:
            gpa = float(gpa_list[0])
        plan_list = re.findall(
            r"计划总课程(\d+)门通过(\d+)门?.*未通过(\d+)门?.*未修(\d+)?.*在读(\d+)门?.*计划外?.*通过(\d+)门?.*未通过(\d+)门",
            display_statistics,
        )
        if len(plan_list) == 0 or len(plan_list[0]) < 7:
            return {"gpa": gpa}
        plan_list = plan_list[0]
        return {
            "gpa": gpa,  # 平均学分绩点GPA
            "planed_courses": {
                "total": int(plan_list[0]),  # 计划内总课程数
                "passed": int(plan_list[1]),  # 计划内已过课程数
                "failed": int(plan_list[2]),  # 计划内未过课程数
                "missed": int(plan_list[3]),  # 计划内未修课程数
                "in": int(plan_list[4]),  # 计划内在读课程数
            },
            "unplaned_courses": {
                "passed": int(plan_list[5]),  # 计划外已过课程数
                "failed": int(plan_list[6]),  # 计划外未过课程数
            },
        }

    @classmethod
    def get_academia_type_statistics(cls, content: str):
        finder = re.findall(
            r"\"(.*)&nbsp.*要求学分.*:([0-9]{1,}[.][0-9]*|0|&nbsp;).*获得学分.*:([0-9]{1,}[.][0-9]*|0|&nbsp;).*未获得学分.*:([0-9]{1,}[.][0-9]*|0|&nbsp;)[\s\S]*?<span id='showKc(.*)'></span>",
            content,
        )
        finder_list = list({}.fromkeys(finder).keys())
        academia_list = [
            list(i)
            for i in finder_list
            if i[0] != ""  # 类型名称不为空
            and len(i[0]) <= 20  # 避免正则到首部过长类型名称
            and "span" not in i[-1]  # 避免正则到尾部过长类型名称
            and i[0] not in cls.ignore_type  # 忽略的类型名称
        ]
        result = {
            i[0]: {
                "id": i[-1],
                "credits": {
                    "required": i[1] if cls.is_number(i[1]) and i[1] != "0" else None,
                    "earned": i[2] if cls.is_number(i[2]) and i[2] != "0" else None,
                    "missed": i[3] if cls.is_number(i[3]) and i[3] != "0" else None,
                },
            }
            for i in academia_list
        }
        return result

    @classmethod
    def get_display_term(cls, sid, year, term):
        """
        计算培养方案具体学期转化成中文
        note: 留级和当兵等情况会不准确
        """
        if (sid and year and term) is None:
            return None
        grade = int(sid[0:2])
        year = int(year[2:4])
        term = int(term)
        dict = {
            grade: "大一上" if term == 1 else "大一下",
            grade + 1: "大二上" if term == 1 else "大二下",
            grade + 2: "大三上" if term == 1 else "大三下",
            grade + 3: "大四上" if term == 1 else "大四下",
        }
        return dict.get(year)

    @classmethod
    def split_merge_display(cls, schedule):
        """
        拆分同周同天同课程不同时段数据合并的问题
        """
        repetIndex = []
        count = 0
        for items in schedule["courses"]:
            for index in range(len(schedule["courses"])):
                if (schedule["courses"]).index(items) == count:  # 如果对比到自己就忽略
                    continue
                elif (
                    items["course_id"]
                    == schedule["courses"][index]["course_id"]  # 同周同天同课程
                    and items["weekday"] == schedule["courses"][index]["weekday"]
                    and items["weeks"] == schedule["courses"][index]["weeks"]
                ):
                    repetIndex.append(index)  # 满足条件记录索引
            count += 1  # 记录当前对比课程的索引
        if len(repetIndex) % 2 != 0:  # 检测到同一课程在一天内存在多个时段，当前逻辑不处理此情况
            return schedule
        for r in range(0, len(repetIndex), 2):  # 索引数组两两成对，故步进2循环
            fir = repetIndex[r]
            sec = repetIndex[r + 1]
            if len(re.findall(r"(\d+)", schedule["courses"][fir]["sessions"])) == 4:
                schedule["courses"][fir]["sessions"] = (
                    re.findall(r"(\d+)", schedule["courses"][fir]["sessions"])[0]
                    + "-"
                    + re.findall(r"(\d+)", schedule["courses"][fir]["sessions"])[1]
                    + "节"
                )
                schedule["courses"][fir]["list_sessions"] = cls.list_sessions(
                    schedule["courses"][fir]["sessions"]
                )
                schedule["courses"][fir]["time"] = cls.display_course_time(
                    schedule["courses"][fir]["sessions"]
                )

                schedule["courses"][sec]["sessions"] = (
                    re.findall(r"(\d+)", schedule["courses"][sec]["sessions"])[2]
                    + "-"
                    + re.findall(r"(\d+)", schedule["courses"][sec]["sessions"])[3]
                    + "节"
                )
                schedule["courses"][sec]["list_sessions"] = cls.list_sessions(
                    schedule["courses"][sec]["sessions"]
                )
                schedule["courses"][sec]["time"] = cls.display_course_time(
                    schedule["courses"][sec]["sessions"]
                )
        return schedule

    @classmethod
    def split_notifications(cls, item):
        if not item.get("xxnr"):
            return {"type": None, "content": None}
        content_list = re.findall(r"(.*):(.*)", item["xxnr"])
        if len(content_list) == 0:
            return {"type": None, "content": item["xxnr"]}
        return {"type": content_list[0][0], "content": content_list[0][1]}

    @classmethod
    def get_place(cls, place):
        return place.split("<br/>")[0] if "<br/>" in place else place

    @classmethod
    def get_course_time(cls, time):
        return "、".join(time.split("<br/>")) if "<br/>" in time else time

    @classmethod
    def is_number(cls, s):
        if s == "":
            return False
        try:
            float(s)
            return True
        except ValueError:
            pass
        try:
            for i in s:
                unicodedata.numeric(i)
            return True
        except (TypeError, ValueError):
            pass
        return False
