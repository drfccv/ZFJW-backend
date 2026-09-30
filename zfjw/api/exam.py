"""考试安排。"""
import json
import time
import traceback
from typing import Optional
from pyquery import PyQuery as pq
from requests import exceptions


class ExamMixin:
    def get_exam_schedule(self, year: int, term: int = 0, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取考试信息"""
        try:
            # 首先尝试从配置获取exam URL
            url = self.get_school_url('exam', None, school_name, base_url)
            # 如果配置的URL不包含doType=query，则添加
            if 'doType=query' not in url:
                # 添加doType=query参数
                separator = '&' if '?' in url else '?'
                url = f"{url}{separator}doType=query"
        except ValueError:
            # 如果配置获取失败，使用默认URL
            fallback_base = base_url or self.base_url or ""
            url = f"{fallback_base.rstrip('/')}/kwgl/kscx_cxXsksxxIndex.html?doType=query&gnmkdm=N358105"
        temp_term = term
        term = term**2 * 3
        term = 0 if term == 0 else term
        data = {
            "xnm": str(year),  # 学年数
            "xqm": str(term),  # 学期数，第一学期为3，第二学期为12, 全学年为空''
            "_search": "false",
            "nd": int(time.time() * 1000),
            "queryModel.showCount": "100",  # 每页最多条数
            "queryModel.currentPage": "1",
            "queryModel.sortName": "",
            "queryModel.sortOrder": "asc",            "time": "0",  # 查询次数
        }
        try:
            req_grade = self.sess.post(
                url,
                headers=self.headers,
                data=data,
                timeout=self.timeout,
                verify=False,
            )
            
            if req_grade.status_code != 200:
                # 非 200 状态码：先检查是否被重定向到了登录页面（session 过期）
                if req_grade.status_code in (901, 302, 401):
                    try:
                        login_doc = pq(req_grade.text)
                        if login_doc("h5").text() == "用户登录":
                            return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
                    except Exception:
                        pass
                    if "login" in req_grade.url.lower():
                        return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
                return {"code": 2333, "msg": "教务系统服务异常"}
            doc = pq(req_grade.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            
            # 解析JSON响应
            try:
                grade = req_grade.json()
            except json.JSONDecodeError as json_err:
                return {"code": 2333, "msg": f"响应格式错误: {str(json_err)}"}
                
                
            grade = req_grade.json()
            grade_items = grade.get("items")
            if not grade_items:
                return {"code": 1005, "msg": "获取内容为空"}
            result = {
                "sid": grade_items[0]["xh"],
                "name": grade_items[0]["xm"],
                "year": year,
                "term": temp_term,
                "count": len(grade_items),
                "courses": [
                    {
                        "course_id": i.get("kch"), # 课程代码
                        "title": i.get("kcmc"), # 课程名称
                        "time": i.get("kssj"), # 考试时间信息
                        "location": i.get("cdmc"), # 考试地点
                        "xq": i.get("cdxqmc"), # 考试校区
                        "zwh": i.get("zwh"), # 考试座号
                        "cxbj": i.get("cxbj", ""), # 重修标记
                        "exam_name": i.get("ksmc"), # 考试批次名
                        "teacher": i.get("jsxx"), # 任课教师(含教师id)
                        "class_name": i.get("jxbmc"), # 教学班名称
                        "kkxy": i.get("kkxy"), # 开课学院
                        "credit": self.align_floats(i.get("xf")), # 课程学分数
                        "ksfs": i.get("ksfs"), # 考试方式, ep: 笔试 & 开卷 & 机考
                        "sjbh": i.get("sjbh"), # 试卷编号
                        "bz": i.get("bz1", ""), # 备注, ep: 免监考班级
                    }
                    for i in grade_items
                ],
            }
            return {"code": 1000, "msg": "获取考试信息成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取考试信息超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取考试信息时未记录的错误：" + str(e)}
